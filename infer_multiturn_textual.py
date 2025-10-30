import argparse
import os
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import tqdm

from utils import (
    parse_files, dump_files, load_frontalk_dataset, request, n_turns, load_messages, dump_messages,
    request_with_truncation
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

USER_PROMPT_FUNCTION = """You are provided with instructions to **add or refine functionalities** of a website. Your task is to refine the instructions so they are accurate, specific, and actionable. Use the code of the existing website as context.
1. **Verify component or functionality references.** These references typically involve **where** to implement the new feature, or **how** to navigate to the new feature from the homepage.
   * If a referenced component/functionality exists, refine vague references to be more precise.
     * Example: Change "add a button to the main menu" to "add a button to the dark gray navigation bar at the top".
   * If it does **not** exist, clearly note that it must be implemented before the instruction can be applied.
2. **Clarify vague instructions.** If an instruction is not specific enough, make it more concrete based on the actual website.
3. **Avoid code-level details.** Do not reference class names, HTML attributes, color hex codes, or other implementation-specific identifiers.

Your refined instructions should be a short paragraph (3–6 sentences). Start your refined instructions with
**Response:**

# Instructions to Refine

{{{INSTRUCTIONS}}}

# Code for Existing Website

{{{CODE}}}"""

USER_PROMPT_DESIGN = """You are provided with instructions to **refine the visual design** of a website. Your task is to refine the instructions so they are accurate, specific, and actionable. Use the code of the existing website as context.
1. **Check for already implemented instructions.** Compare each instruction to the current state of the website. If an instruction is already implemented, remove it from the refined list.
   * Example: If the instruction says "Use a two-column layout" but the site already has a two-column layout, remove that instruction.
   * Keep all unfulfilled instructions exactly as they are — **do not omit or change them** unless covered by steps 2–3 below.
2. **Verify component or functionality references.**
   * If a referenced component/functionality exists, refine vague references to be more precise.
     * Example: Change "the button" to "the green submit button in the bottom left".
   * If it does **not** exist, clearly note that it must be implemented before the instruction can be applied.
3. **Clarify vague instructions.** If an instruction is not specific enough, make it more concrete based on the actual website.
4. **Avoid code-level details.** Do not reference class names, HTML attributes, color hex codes, or other implementation-specific identifiers.

Your refined instructions should be a short paragraph (~5 sentences). Start your refined instructions with
**Response:**

# Instructions to Refine

{{{INSTRUCTIONS}}}

# Code for Existing Website

{{{CODE}}}"""

N_TURNS_PER_DATA = 10


def simulate_user(user_kwargs, i, data, html_dir=None):
    instructions = data['cases'][i]['instructions']
    if i == 0:
        return instructions

    assert html_dir is not None
    code = ""
    files = [os.path.join(dp, f) for dp, dn, fn in os.walk(html_dir) for f in fn]
    for fn in files:
        extension = fn.split('.')[-1]
        if extension in ['html', 'css', 'js', ]:
            with open(fn) as f:
                text = f.read()
            code += f"\n\n## {os.path.relpath(fn, html_dir)}\n```{extension}\n{text.strip()}\n```"
    code = code.strip()

    instruction_type = data['cases'][i]['type']
    prompt = dict(function=USER_PROMPT_FUNCTION, design=USER_PROMPT_DESIGN)[instruction_type]. \
        replace("{{{INSTRUCTIONS}}}", instructions).replace("{{{CODE}}}", code)

    for _ in range(5):  # <- retry 5 times
        response = request([{"role": "user", "content": prompt}, ], **user_kwargs)
        assert response is not None
        if "Response:" in response:
            response = response.split("Response:")[-1].strip()
            if response.startswith("**"):
                response = response[2:].strip()
            return response


def main_func(data, args, messages):
    request_kwargs = {'model': args.openai_model, 'openai_api_key': args.local_openai_key,
                      'local_openai_port': args.local_openai_port}
    if args.max_tokens is not None:
        request_kwargs['max_tokens'] = args.max_tokens
    user_kwargs = dict(model=args.user_model)

    if len(messages) == 0:  # initialize message
        messages = [{'role': 'system', 'content': PROMPT}]

    # request i-th turn
    i = n_turns(messages)
    assert i < N_TURNS_PER_DATA
    if i == 0:
        last_out_dirname_ = None
    else:
        last_out_dirname_ = os.path.join(args.out_dirname, f't.{i - 1}', data['id'].replace('.json', ".html"))

    # request by dynamic user message
    msg = simulate_user(user_kwargs, i, data, html_dir=last_out_dirname_)
    # request
    messages.append({"role": "user", "content": msg})

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


def get_simple_navigation(data, messages=None):
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
            '  <h1>Navigation Page</h1>',
            '  <div style="margin-bottom:12px;">',
            '    <label><input type="checkbox" checked onclick="toggleRows(\'row1\', this.checked)"> Row 1: Instructions</label> ',
            '    <label><input type="checkbox" checked onclick="toggleRows(\'row2\', this.checked)"> Row 2: Type</label> ',
            '    <label><input type="checkbox" checked onclick="toggleRows(\'row3\', this.checked)"> Row 3: Message</label> ',
            '    <label><input type="checkbox" checked onclick="toggleRows(\'row4\', this.checked)"> Row 4: Test Conditions</label> ',
            '    <label><input type="checkbox" checked onclick="toggleRows(\'row5\', this.checked)"> Row 5: Links</label>',
            '  </div>',
            '  <script>',
            '    function toggleRows(cls, show) {',
            '      document.querySelectorAll("."+cls).forEach(function(tr){',
            '        tr.style.display = show ? "" : "none";',
            '      });',
            '    }',
            '  </script>']

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
            html.append(
                f'<td style="border: 1px solid black; padding: 8px; text-align: left; font-size: 8px;">{popup_text}</td>')
        html.append('    </tr>')

        # Row 2: Type
        html.append('    <tr class="row2">')
        for i in range(N_TURNS_PER_DATA):
            popup_text = 'type=' + d['cases'][i]['type']
            html.append(
                f'<td style="border: 1px solid black; padding: 8px; text-align: left; font-size: 8px;">{popup_text}</td>')
        html.append('    </tr>')

        # Row 3: Message content (assistant replies)
        html.append('    <tr class="row3">')
        for i in range(N_TURNS_PER_DATA):
            if messages is not None and len(messages.get(d["id"], [])) > 2 * i + 1:
                popup_text = messages[d["id"]][2 * i + 1]["content"]
            else:
                popup_text = "-"
            html.append(
                f'<td style="border: 1px solid black; padding: 8px; text-align: left; font-size: 8px;">{popup_text}</td>')
        html.append('    </tr>')

        # Row 4: Test conditions
        html.append('    <tr class="row4">')
        for i in range(N_TURNS_PER_DATA):
            popup_text = '<br>'.join([x['condition'] for x in d['cases'][i]['test_conditions']])
            html.append(
                f'<td style="border: 1px solid black; padding: 8px; text-align: left; font-size: 8px;">{popup_text}</td>')
        html.append('    </tr>')

        # Row 5: Links
        html.append('    <tr class="row5">')
        for i in range(N_TURNS_PER_DATA):
            path = f't.{i}/{dir_name}/index.html'
            html.append(
                f'      <td style="border: 1px solid black; padding: 8px; text-align: center;"><a href="{path}">t.{i}</a></td>')
        html.append('    </tr>')

        html.append('  </table>')

    html.append('</body>')
    html.append('</html>')

    return '\n'.join(html)


def main_(args):
    os.makedirs(args.out_dirname, exist_ok=True)

    data = load_frontalk_dataset()

    messages_all = {}
    total = len(data) * N_TURNS_PER_DATA
    messages_fname = os.path.join(args.out_dirname, "messages.jsonl")
    if os.path.exists(messages_fname):
        print("Load existing messages:", messages_fname)
        messages_all = load_messages(messages_fname)
        total = sum([N_TURNS_PER_DATA - n_turns(messages_all.get(d['id'])) for d in data])
    with open(os.path.join(args.out_dirname, "navigation.html"), "w") as f:
        f.write(get_simple_navigation(data, messages_all))

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
            if pbar.n % 20 == 0:
                with open(os.path.join(args.out_dirname, "navigation.html"), "w") as f:
                    f.write(get_simple_navigation(data, messages_all))


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
    args.user_model = 'gpt-4o'  # <- hardcode as gpt-4o

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
