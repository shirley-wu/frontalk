import argparse
import json
import os
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import tqdm

from draw.main import draw
from utils import (
    parse_files, dump_files, load_frontalk_dataset, encode_pil_image, n_turns, load_messages, dump_messages,
    request_with_truncation,
)

PROMPT = """Write a website based on the instructions below. Requirements:
1. You will receive a sequence of user instructions. Follow each new instruction while preserving all requirements from previous instructions.
2. You may generate one or multiple files if needed. The website homepage (the first page users land on) should be named `index.html`.
3. Ensure that every implemented feature is accessible **from the homepage** — either directly displayed on the homepage or reachable through navigation starting from the homepage.
4. Generate realistic pseudo-data to demonstrate the full functionalities. If the feature involves multiple entries (e.g., a product catalog, blog list, etc.), generate **at least 5** pseudo entries.
5. For multimedia content, **always** use placeholder: use `placeholder.png` for images, `placeholder.mp4` for videos, `placeholder.mp3` for audios, and `placeholder.pdf` for pdf files.

# Output Format

For each file, use the following format:

## filename.html
```html
[code]
```"""

PROMPTS_BY_ASPECT = {
    "function": "Implement or refine the functionality as in the image visualization",
    "design": "Refine the visual design as in the image visualization",
}

N_TURNS_PER_DATA = 10


def main_func(data, args, messages):
    request_kwargs = {'model': args.openai_model, 'openai_api_key': args.local_openai_key,
                      'local_openai_port': args.local_openai_port}
    if args.max_tokens is not None:
        request_kwargs['max_tokens'] = args.max_tokens
    drawer_kwargs = dict(model=args.drawer_model)

    if len(messages) == 0:  # initialize message
        system_prompt = PROMPT.replace("{{{GOAL}}}", data['summary']['purpose'])
        messages = [{'role': 'system', 'content': system_prompt}]

        # request i-th turn
    i = n_turns(messages)
    assert i < N_TURNS_PER_DATA
    if i == 0:
        last_out_dirname_ = None
    else:
        last_out_dirname_ = os.path.join(args.out_dirname, f't.{i - 1}', data['id'].replace('.json', ".html"))

    # draw
    instruction_type = data['cases'][i]['type']
    image, drawing_messages = draw(drawer_kwargs, i, instruction_type, data, html_dir=last_out_dirname_)
    # save intermediate drawing results
    draw_out_dirname = os.path.join(args.out_dirname, 'draw', data['id'].replace('.json', '.html'))
    os.makedirs(draw_out_dirname, exist_ok=True)
    with open(os.path.join(draw_out_dirname, f'{i}-messages.json'), 'w') as f:
        json.dump(drawing_messages, f)

    # request by image
    messages.append({"role": "user", "content": [
        {"type": "text", "text": PROMPTS_BY_ASPECT[instruction_type]},
    ]})
    if image is not None:
        image.save(os.path.join(draw_out_dirname, f'{i}.png'))
        messages[-1]['content'].append({"type": "image_url", "image_url": {
            "url": "data:image/jpeg;base64,{}".format(encode_pil_image(image))
        }})

    # iteratively request, until NOT overlength
    response = request_with_truncation(messages=messages, data_id=data['id'], **request_kwargs)
    messages.append({"role": "assistant", "content": response})

    # output
    out_dirname_ = os.path.join(args.out_dirname, f't.{i}', data['id'].replace('.json', ".html"))
    shutil.rmtree(out_dirname_, ignore_errors=True)
    if i > 0:  # copy last
        shutil.copytree(last_out_dirname_, out_dirname_)
    else:
        os.makedirs(out_dirname_, exist_ok=True)
    files = parse_files(response, out_dirname_)
    dump_files(files, out_dirname_)

    return data, messages, i == N_TURNS_PER_DATA - 1


def get_simple_navigation(data):
    html = ['<!DOCTYPE html>',
            '<html>',
            '<head>',
            '  <meta charset="UTF-8">',
            '  <title>Simple Navigation</title>',
            '  <style>',
            '    body { font-family: sans-serif; padding: 20px; }',
            '    h2 { margin-top: 30px; }',
            '    table { border-collapse: collapse; margin-bottom: 20px; }',
            '    td { padding-right: 24px; padding-bottom: 8px; }',
            '    a { text-decoration: none; }',
            '  </style>',
            '</head>',
            '<body>',
            '  <h1>Navigation Page</h1>']

    # Global toggles + popup scaffolding
    html.append('''
    <div style="margin: 12px 0;">
      <label><input type="checkbox" checked onclick="toggleRows('row1', this.checked)"> Row 1: Instructions</label>
      <label><input type="checkbox" checked onclick="toggleRows('row2', this.checked)"> Row 2: Type</label>
      <label><input type="checkbox" checked onclick="toggleRows('row3', this.checked)"> Row 3: Image</label>
      <label><input type="checkbox" checked onclick="toggleRows('row4', this.checked)"> Row 4: Test Conditions</label>
      <label><input type="checkbox" checked onclick="toggleRows('row5', this.checked)"> Row 5: Links</label>
    </div>

    <div id="overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%;
         background:rgba(0,0,0,0.3); z-index:999;" onclick="hidePopup()"></div>
    <div id="popup" style="display:none; position:fixed; top:30%; left:50%; transform:translate(-50%, -30%);
         padding:20px; background:white; border:2px solid black; z-index:1000; box-shadow:0 0 10px rgba(0,0,0,0.5);
         max-width:90%; max-height:90%; overflow:auto;"></div>

    <script>
      function showPopup(content) {
        document.getElementById('popup').innerHTML = content; // allow image HTML
        document.getElementById('popup').style.display = 'block';
        document.getElementById('overlay').style.display = 'block';
      }
      function hidePopup() {
        document.getElementById('popup').style.display = 'none';
        document.getElementById('overlay').style.display = 'none';
      }
      function toggleRows(cls, show) {
        document.querySelectorAll('.' + cls).forEach(function(tr) {
          tr.style.display = show ? '' : 'none';
        });
      }
    </script>
    ''')

    # Loop to build tables
    for d in data:
        dir_name = d['id'].replace('.json', ".html")
        html.append(f'  <h2>{dir_name}</h2>')
        html.append(f"<p>{d['summary']['purpose']}</p>")
        html.append('  <table style="border-collapse: collapse;">')

        # Row 1: Instructions
        html.append('    <tr class="row1">')
        for i in range(N_TURNS_PER_DATA):
            popup_text = d['cases'][i]['instructions']
            html.append(f'<td style="border: 1px solid black; padding: 8px; text-align: left; font-size: 8px;">'
                        f'{popup_text}</td>')
        html.append('    </tr>')

        # Row 2: Type
        html.append('    <tr class="row2">')
        for i in range(N_TURNS_PER_DATA):
            popup_text = 'type=' + d['cases'][i]['type']
            html.append(f'<td style="border: 1px solid black; padding: 8px; text-align: left; font-size: 8px;">'
                        f'{popup_text}</td>')
        html.append('    </tr>')

        # Row 3: Image button (popup)
        html.append('    <tr class="row3">')
        for i in range(N_TURNS_PER_DATA):
            image_fname = os.path.join("draw", d['id'], f'{i}.png')
            html.append(
                '      <td style="border: 1px solid black; padding: 8px; text-align: center;">'
                + f"<button onclick=\"showPopup('<img src=\\'{image_fname}\\' alt=\\'Example Image\\' "
                + "style=\\'max-width:100%; height:auto;\\'>')\">Image</button></td>"
            )
        html.append('    </tr>')

        # Row 4: Test conditions
        html.append('    <tr class="row4">')
        for i in range(N_TURNS_PER_DATA):
            popup_text = '<br>'.join([x['condition'] for x in d['cases'][i]['test_conditions']])
            html.append(f'<td style="border: 1px solid black; padding: 8px; text-align: left; font-size: 8px;">'
                        f'{popup_text}</td>')
        html.append('    </tr>')

        # Row 5: Links
        html.append('    <tr class="row5">')
        for i in range(N_TURNS_PER_DATA):
            path = f't.{i}/{dir_name}/index.html'
            html.append(f'      <td style="border: 1px solid black; padding: 8px; text-align: center;">'
                        f'<a href="{path}">t.{i}</a></td>')
        html.append('    </tr>')

        html.append('  </table>')

    html.append('</body>')
    html.append('</html>')

    return '\n'.join(html)


def main_(args):
    os.makedirs(args.out_dirname, exist_ok=True)

    data = load_frontalk_dataset()
    with open(os.path.join(args.out_dirname, "navigation.html"), "w") as f:
        f.write(get_simple_navigation(data))

    messages_all = {}
    total = len(data) * N_TURNS_PER_DATA
    messages_fname = os.path.join(args.out_dirname, "messages.jsonl")
    if os.path.exists(messages_fname):
        print("Load existing messages:", messages_fname)
        messages_all = load_messages(messages_fname)
        total = sum([N_TURNS_PER_DATA - n_turns(messages_all.get(d['id'])) for d in data])

    finished_all = {d['id']: n_turns(messages_all.get(d['id'])) == N_TURNS_PER_DATA for d in data}
    pbar = tqdm.tqdm(total=total)
    with ProcessPoolExecutor(max_workers=args.num_workers) as exe:
        # map each future -> its (x,i) so we know how to chain
        future_to_args = [exe.submit(main_func, d, args, messages_all.get(d['id'], []))
                          for d in data if not finished_all[d['id']]]
        while not all(finished_all.values()):
            # wait for the next future to complete
            fut = next(as_completed(future_to_args))
            d, messages, finished = fut.result()
            dump_messages(messages_fname, d['id'], messages_all.get(d['id']), messages)
            messages_all[d['id']] = messages
            finished_all[d['id']] = finished
            # remove the completed future
            future_to_args.remove(fut)
            if not finished:
                future_to_args.append(exe.submit(main_func, d, args, messages_all[d['id']]))
            pbar.update()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out_dirname', type=str)
    parser.add_argument("--local_openai_port", default=None, nargs="+")
    parser.add_argument("--local_openai_key", default=None)
    parser.add_argument("--openai_model", default="gpt-4o")
    parser.add_argument("--num_workers", default=16, type=int)
    parser.add_argument("--max_tokens", default=None, type=int)
    parser.add_argument("--keep_retrying", default=False, action="store_true")
    args = parser.parse_args()
    args.drawer_model = 'gpt-4o'  # <- hardcode as gpt-4o

    if args.keep_retrying:
        while True:
            try:
                main_(args)
            except:
                time.sleep(10)
            else:
                break
    else:
        main_(args)


if __name__ == "__main__":
    main()
