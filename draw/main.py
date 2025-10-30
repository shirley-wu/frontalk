import ast
import glob
import json
import os
import re
import shutil
import subprocess
import uuid
from typing import List

from PIL import Image
from openai import OpenAI
from selenium.common.exceptions import NoAlertPresentException

from draw.tools import get_html_state, driver_get_safe, CODE_HEAD, CODE_TAIL
from utils import request, encode_pil_image, encode_image
from webvoyager.run import get_default_driver

D = os.path.dirname(__file__)
PROMPT = {}
for fname in glob.glob(os.path.join(D, '*.md')):
    with open(fname) as f:
        PROMPT[os.path.basename(fname)] = f.read().strip()


def extract_all_code_segments(text):
    pattern = r"```python(.*?)```"
    code_blocks = re.findall(pattern, text, re.DOTALL)
    ret = [block.strip() for block in code_blocks]
    return '\n\n'.join(ret)


def remove_function_definition(code: str, function_names: List[str]) -> str:
    class FunctionRemover(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            if node.name in function_names:
                return None  # Remove this node
            return node

        def visit_AsyncFunctionDef(self, node):
            if node.name in function_names:
                return None  # Also handle async functions
            return node

    try:
        tree = ast.parse(code)
    except:
        return ""

    tree = FunctionRemover().visit(tree)
    ast.fix_missing_locations(tree)

    try:
        # For Python 3.9+
        new_code = ast.unparse(tree)
    except AttributeError:
        import astor
        new_code = astor.to_source(tree)

    return new_code


def run(response, last_code, key):
    dirpath = os.path.join(os.environ['HOME'], 'tmp', key)
    os.makedirs(dirpath, exist_ok=True)

    code = extract_all_code_segments(response)
    code = remove_function_definition(code, ["text_annotation", "layout_visualization", ])
    code = code.replace('plt.show()', '').strip()
    # prepend last_code
    code = last_code = last_code + '\n\n' + code  # <- last_code is a "clean" version for next round

    # add head and tail
    code = CODE_HEAD.replace("{{{KEY}}}", repr(key)) + '\n\n' + code
    code = code + '\n\n' + CODE_TAIL.replace("{{{KEY}}}", repr(key))

    # run python
    fname = os.path.join(dirpath, 'main.py')
    with open(fname, 'w') as f:
        f.write(code)

    result = subprocess.run(['python', 'main.py', ], cwd=dirpath, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        error_msg = result.stderr.strip() or "Unknown error"
        raise RuntimeError(error_msg)

    return last_code


def read_html_layout(key, last_n_layout):
    n_layout = len(glob.glob(os.path.join(os.environ['HOME'], 'tmp', key, 'coordinates-*.json')))
    ret = []
    for i in range(last_n_layout, n_layout):
        with open(os.path.join(os.environ['HOME'], 'tmp', key, f'coordinates-{i}.json')) as f:
            ret.append(f.read())
    return n_layout - last_n_layout, ret


USER_PROMPT_EXISTING_WEBSITE = """Information for page {{{PAGE_NAME}}}

# Screenshot filename: {{{IMG_NAME}}}

# HTML

{{{CODE}}}

# Coordinates

{{{COORDS}}}"""


def draw(client_kwargs, i, t, data, html_dir=None):
    uuid_key = str(uuid.uuid4())
    tmp_path = os.path.join(os.environ['HOME'], 'tmp', uuid_key)
    os.makedirs(tmp_path, exist_ok=True)

    if t == "function":
        if i == 0:
            prompt = PROMPT['agent_system_1-1.md']  # drawing based on empty canvas
        else:
            prompt = PROMPT['agent_system_x-1.md']  # navigate to homepage
    else:
        assert t == "design"
        prompt = PROMPT[f'agent_system_x-2.md']

    # pure text instructions
    instructions = data['cases'][i]['instructions']
    prompt = prompt.replace("{{{INSTRUCTIONS}}}", instructions)
    messages = [{'role': 'user', 'content': prompt}, ]

    # then, append images if the website already exists
    if i > 0:  # visualize the existing websites if any
        driver = get_default_driver(tmp_path)
        assert html_dir is not None
        for fn in glob.glob(os.path.join(html_dir, "**", "*.html"), recursive=True):
            success = driver_get_safe(driver, 'file://' + os.path.abspath(fn))
            if success:
                basename = os.path.relpath(fn, start=html_dir)
                image_fname = os.path.join(
                    tmp_path, 'screenshot_' + basename.replace("/", "_").replace(".html", ".png")
                )
                try:
                    try:  # just quickly abort the alert
                        alert = driver .switch_to.alert
                        alert.accept()
                    except NoAlertPresentException:
                        pass
                    html, coord = get_html_state(driver, image_fname, dont_quit=True)
                except Exception as e:
                    print("Weird error when loading html")
                    print(e)
                else:
                    prompt = USER_PROMPT_EXISTING_WEBSITE.replace("{{{PAGE_NAME}}}", basename). \
                        replace("{{{IMG_NAME}}}", os.path.basename(image_fname)). \
                        replace("{{{CODE}}}", html.strip()). \
                        replace("{{{COORDS}}}", json.dumps(coord, indent=2))
                    messages.append({'role': 'user', 'content': [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": "data:image/jpeg;base64,{}".format(encode_image(image_fname))
                        }},
                    ]})
        driver.quit()

        if len(messages) == 1:
            messages[0]['content'] += "\n\n# Screenshot, HTML and Coordinates of Existing Website" \
                                      "\n\nUnavailable for now"

    last_code = ''
    last_n_layout = 0
    image = None

    for _ in range(3):  # <- At most 3 turns
        n_retry = 0
        while True:
            uuid_key = str(uuid.uuid4())
            os.makedirs(os.path.join(os.environ['HOME'], 'tmp', uuid_key), exist_ok=True)
            for x in glob.glob(os.path.join(tmp_path, '*.png')):
                shutil.copy(x, os.path.join(os.environ['HOME'], 'tmp', uuid_key))

            try:
                # request
                response = request(messages=messages, **client_kwargs)
                if len(messages) > 1 and response.startswith('YES'):  # no more turns
                    break

                # run code
                last_code = run(response, last_code, uuid_key)
                image = Image.open(os.path.join(os.environ['HOME'], 'tmp', uuid_key, 'main.png'))
                n_layout, layout_jsons = read_html_layout(uuid_key, last_n_layout)  # <- this is BEFORE rmtree
                last_n_layout = n_layout
                break
            except Exception as e:
                print("Generated code has error:")
                print(e)
            finally:
                shutil.rmtree(os.path.join(os.environ['HOME'], 'tmp', uuid_key))

            n_retry += 1
            if n_retry >= 3:
                print("-" * 10, "Generated code fails after retrying!!! RETURN!!!!")
                shutil.rmtree(tmp_path)
                return image, messages

        if len(messages) > 1 and response.startswith('YES'):  # no more turns
            break
        # append message
        messages.append({'role': 'assistant', 'content': response})

        # parse html layout - if any
        if n_layout > 0:
            prompt = PROMPT['agent_later_turns.html.md'].replace("{{{N}}}", str(n_layout))
            prompt += '\n\n' + '\n\n'.join(layout_jsons)
        else:
            prompt = PROMPT['agent_later_turns.no-html.md']

        # run
        messages.append({'role': 'user', 'content': [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": "data:image/jpeg;base64,{}".format(encode_pil_image(image)),
            }}
        ]})

    shutil.rmtree(tmp_path)
    return image, messages
