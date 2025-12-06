import multiprocessing
import os
import sys
from functools import partial

import numpy as np
import tqdm

from utils import load_frontalk_dataset, request

PROMPT = """You are an expert front-end code auditor. Your task is to evaluate a generated website against a set of user instructions to detect **unwanted features**.

Implemented features can be generally categorized into three types:
1. Explicit Feature: Directly requested in the User Instructions.
2. Implicit/Necessary Feature: Not explicitly asked for, but required for the code to function (e.g., a submit button for a requested form) or standard best practices (e.g., input validation, basic accessibility, responsive layout).
3. Unwanted Feature: A distinct functionality, section, or business logic that was neither requested nor implied by the requested features. (e.g., adding a "Blog" section to a login page, or a "Dark Mode" toggle when not requested).

Task Instructions:
1. Analyze the Code: List every distinct functional component and UI element found in the code.
2. Map to Instructions: For each item listed, determine if it is "Explicit," "Implicit/Necessary," or "Unwanted."
3. Justify: If you identify a potential Unwanted Feature, explain why it is not a reasonable inference from the instructions.

Think step by step to perform the analysis. After your analysis, end your response strictly with: Response: [Yes/No] (Note: "Yes" means unwanted features exist. "No" means the code is clean.)

# Instructions

{{{INST}}}

# Code

Note: `index.html` is the homepage.

{{{CODE}}}"""


def represent_code_state(html_dir):
    code = ""
    files = [os.path.join(dp, f) for dp, dn, fn in os.walk(html_dir) for f in fn]
    for fn in files:
        extension = fn.split('.')[-1]
        if extension in ['html', 'css', 'js', ]:
            with open(fn) as f:
                text = f.read()
            code += f"\n\n## {os.path.relpath(fn, html_dir)}\n```{extension}\n{text.strip()}\n```"
    code = code.strip()
    return code


def func(data, exp, request_kwargs):
    code = represent_code_state(os.path.join(exp, data['id']))
    instructions = '\n\n'.join([c['instructions'] for c in data['cases']])
    prompt = PROMPT.replace("{{{CODE}}}", code).replace("{{{INST}}}", instructions)
    response = request([{'role': 'user', 'content': prompt}, ], **request_kwargs)
    return response, "Response: Yes".lower() in response.lower() or \
                     "Response: [Yes]".lower() in response.lower()


def main(exp):
    data = load_frontalk_dataset()
    request_kwargs = dict(model='gpt-5-mini', max_tokens=None)

    unwanted_ratio = []
    with multiprocessing.Pool(16) as p:
        for r, x in tqdm.tqdm(p.imap(
                partial(func, exp=exp, request_kwargs=request_kwargs), data
        ), total=len(data)):
            if x:
                import pdb
                pdb.set_trace()
            unwanted_ratio.append(x)
    print(np.mean(unwanted_ratio))


if __name__ == "__main__":
    _, dir_to_evaluate = sys.argv
    main(dir_to_evaluate)
