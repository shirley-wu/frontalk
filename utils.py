import base64
import copy
import hashlib
import json
import os
import re
import time
from io import BytesIO

from PIL import Image
from openai import OpenAI


def parse_single_file(text):
    filename = text.splitlines()[0].strip().split('(')[0].strip()
    while True:
        still_starts_with_sep = False
        for sep in ['# ', '## ', '### ', '#### ', '##### ', ]:
            if filename.startswith(sep):
                still_starts_with_sep = True
                filename = filename[len(sep):].strip()
        if not still_starts_with_sep:
            break

    if filename.endswith('`'):  # remove trailing '`'
        filename = filename[:-1]
    if '`' in filename:  # remaining ` indicates start of filename
        filename = filename.split('`')[1].strip()
    extension = filename.split('.')[-1]
    if '```' + extension in text:
        content = text.split('```' + extension)[-1].strip().split('```')[0].strip()
    elif extension == 'js' and '```javascript' in text:
        content = text.split('```javascript')[-1].strip().split('```')[0].strip()
    elif '```' not in text:
        content = '\n'.join(text.splitlines()[1:])
    else:
        content = text.split('```')[1]
        content = '\n'.join(content.splitlines()[1:])
        content = content.split('```')[0].strip()

    return filename, content


def parse_files(text, out_dir):
    text = '\n\n' + text.strip()
    ret = {}
    text = re.split(r'\n# |\n## |\n### |\n#### |\n##### ', text)
    for x in text[1:]:
        filename, content = parse_single_file(x)
        if filename is not None and filename != '':
            for placeholder_fname in ['placeholder.png', 'placeholder.mp4', 'placeholder.mp3', 'placeholder.pdf', ]:
                if placeholder_fname in content:
                    relative_fname = os.path.relpath(os.path.join('./placeholder/', placeholder_fname), start=out_dir)
                    content = content.replace(placeholder_fname, relative_fname)
            ret[filename] = content
    return ret


def dump_files(files, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for filename, content in files.items():
        os.makedirs(os.path.dirname(os.path.join(out_dir, filename)), exist_ok=True)
        with open(os.path.join(out_dir, filename), 'w') as f:
            f.write(content)


def load_frontalk_dataset():
    with open('data.jsonl') as f:
        data = [json.loads(line) for line in f]
    return data


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def encode_pil_image(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")  # or use the format of your choice (e.g., JPEG)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def decode_pil_image(encoded_str: str) -> Image.Image:
    image_data = base64.b64decode(encoded_str)
    buffered = BytesIO(image_data)
    return Image.open(buffered)


def request_(messages, model: str, local_openai_port: int = None, openai_api_key: str = None, max_tokens: int = 10000):
    if 'gemini' in model:
        from google import genai
        from google.genai.types import Content, Part

        def build_gemini_history(messages):
            history = []
            system = []
            for m in messages:
                if m['role'] == 'system':
                    m = copy.deepcopy(m)
                    m['role'] = 'user'
                    assert isinstance(m['content'], str)
                    system.append(m['content'])
                else:
                    role = {'user': 'user', 'assistant': 'model'}[m['role']]
                    if isinstance(m['content'], str):
                        parts_list = [Part.from_text(text=m['content']), ]
                    else:
                        assert isinstance(m['content'], list)
                        assert m['content'][0]['type'] == 'text'
                        assert len(m['content']) <= 2, "Only supporting 1 image per turn right now"
                        parts_list = [Part.from_text(text=m['content'][0]['text']), ]
                        if len(m['content']) == 2:
                            assert m['content'][1]['type'] == 'image_url'
                            image_base64 = m['content'][-1]["image_url"]["url"].split(";base64,")[-1]
                            parts_list.append(Part.from_bytes(
                                data=base64.b64decode(image_base64), mime_type='image/jpeg')
                            )
                    history.append(Content(role=role, parts=parts_list))
            return system, history

        client = genai.Client(api_key=openai_api_key)
        system, history = build_gemini_history(messages)
        chat = client.chats.create(model=model, history=history[:-1])
        generation_config = genai.types.GenerateContentConfig(max_output_tokens=max_tokens)
        if len(system) > 0:
            generation_config.system_instruction = system
        response = chat.send_message(history[-1].parts, config=generation_config)
        return response.text

    if 'claude' in model:
        import anthropic

        def build_claude_messages(messages):
            system = []
            ret = []
            messages = copy.deepcopy(messages)
            for m in messages:
                if m['role'] == 'system':
                    system.append(m['content'])
                else:
                    if isinstance(m['content'], list):
                        for i, mm in enumerate(m['content']):
                            if mm['type'] == 'image_url':
                                m['content'][i] = {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mm["image_url"]["url"].split(";base64,")[0].split(':')[-1],
                                        "data": mm["image_url"]["url"].split(";base64,")[-1],
                                    },
                                }
                    ret.append(m)
            return system, ret

        client = anthropic.Anthropic(api_key=openai_api_key)
        system, messages = build_claude_messages(messages)
        system = '\n'.join(system).strip()
        response = ''
        try:
            with client.messages.stream(model=model, system=system, max_tokens=max_tokens, messages=messages) as stream:
                for text in stream.text_stream:
                    response += text
            return response
        except Exception as e:
            if 'exceed context limit' in str(e) or 'prompt is too long' in str(e):
                # Note: another stupid hack...
                print("Overlength while calling {}: {}".format(model, str(e)[:600]))
                return None  # <- overlength
            raise e

    if local_openai_port is None:
        openai_base_url = None
    else:
        if isinstance(local_openai_port, list):  # use local vllm servers
            # Note: suppose we serve multiple vllm servers; try to send messages with the same first message to the
            # same port (to use prefix cache), using hash
            user_first_msg = json.dumps([m for m in messages if m['role'] == 'user'][0])
            hash_bytes = hashlib.sha256(user_first_msg.encode()).digest()
            hash_int = int.from_bytes(hash_bytes[:8], 'big')
            local_openai_port = local_openai_port[hash_int % len(local_openai_port)]
        assert isinstance(local_openai_port, int) or isinstance(local_openai_port, str)
        openai_base_url = f"http://localhost:{local_openai_port}/v1"

    kwargs = dict(messages=messages, model=model)
    if max_tokens is not None:
        kwargs['max_tokens'] = max_tokens
    client = OpenAI(api_key=openai_api_key, base_url=openai_base_url)

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        if "Please reduce the length of the" in str(e) or \
                "'max_tokens' or 'max_completion_tokens' is too large" in str(e) or \
                "is longer than the maximum model length of" in str(e):  # Note: stupid hack...
            print("Overlength while calling {}: {}".format(model, str(e)[:600]))
            return None  # <- overlength
        else:
            raise e
    return response.choices[0].message.content


def request(messages, model: str, wait_if_fail: int = 60, n_retry: int = 10, **kwargs):
    for _ in range(n_retry):
        try:
            response = request_(messages, model, **kwargs)
            return response
        except Exception as e:
            e = str(e)
            if len(e) > 600:
                e = e[:600] + '...'
            print("Exception while calling {}: {}".format(model, e))
            print(f"Sleep {wait_if_fail}s")
            time.sleep(wait_if_fail)
    raise RuntimeError("Fail even after retrying")


def request_with_truncation(messages, *args, data_id=None, **kwargs):
    response = None
    while response is None:
        response = request(messages=messages, *args, **kwargs)
        if response is None:  # overlength: do truncation
            print("Over-length for data{}: truncate one!".format('' if data_id is None else (' ' + str(data_id))))
            for m in messages:
                if m['role'] == 'assistant' and m['content'] != '(omitted)':
                    m['content'] = '(omitted)'
                    break
    return response


def n_turns(messages):
    if messages is None or len(messages) == 0:
        return 0
    return (len(messages) - 1) // 2


def load_messages(fname, key_subset=None):
    messages_all = {}
    assert fname.endswith(".jsonl")
    with open(fname) as f:
        for line in f:
            o = json.loads(line)
            if len(o) == 3:
                assert o[2] == 'MAY TRUNCATED'
                o = o[:2]  # may truncate
            key, message = o
            if key_subset is not None and key not in key_subset:
                continue
            if key not in messages_all:
                messages_all[key] = []
            messages_all[key].append(message)
    return messages_all


def dump_messages(fname, key, messages_old, messages_new):
    if messages_old is None:
        messages_old = []
    assert len(messages_old) <= len(messages_new)
    may_truncated = messages_new[:len(messages_old)] != messages_old
    with open(fname, 'a') as f:
        for i in range(len(messages_old), len(messages_new)):
            f.write(json.dumps([key, messages_new[i]] + (['MAY TRUNCATED', ] if may_truncated else [])) + '\n')
