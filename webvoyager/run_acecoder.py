import logging
import os
import re
import shutil
import time

from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from utils import encode_image, request, encode_pil_image
from .run import (
    exec_action_click, exec_action_type, exec_action_scroll, exec_action_select
)
from .run_evaluate import (
    setup_logger, setup_task_driver, format_msg, clip_message_and_obs, exec_action_upload, save_transition_video,
    crop_screenshot_for_rect, merge_images, thumbnail_by_max_pixels, format_visual_msg, cleanup_transition_video
)
from .utils import (
    driver_execute_script_safe, get_web_element_rect, extract_information, get_webarena_accessibility_tree,
    print_message, extract_text_from_pdf
)

with open(os.path.join(os.path.dirname(__file__), 'acecoder_prompt.md')) as f:
    OURS_INITIAL_PROMPT = f.read()
OURS_LAST_MSG = "---\n\nYou've reached the step limit for interacting with the website. Please summarize the trajectory so far and analyze whether the instructions have been well met. If not, explain what is missing and what should be included. End your response with Action: ANSWER; PASS or Action: ANSWER; FAIL"


def run_verify_instruction(
        url, goal, instructions, request_kwargs: dict, is_image: bool = False,
        window_width=2048, window_height=1536, image_width=1024, image_height=768,
        max_iter=15, max_attached_imgs=6, text_only=False, fix_box_color=False,
        task_dir=os.path.join(os.environ['HOME'], "tmp/webvoyager_tmp"),
):
    assert text_only is False
    assert fix_box_color is False
    # sanity check
    if is_image:
        assert isinstance(instructions, dict)
    else:
        assert isinstance(instructions, str)

    os.makedirs(task_dir, exist_ok=True)
    setup_logger(task_dir)

    patience = 5
    while True:
        try:
            driver_task, alert_obs = setup_task_driver(
                task_dir, url, window_width, window_height
            )  # <- don't do safe any more LOL
        except Exception as e:
            patience -= 1
            time.sleep(30)
            if patience == 0:
                print("Warning: error keeps happening when opening index.html in `run_acecoder.py`")
                print(e)
                return False, "Browser cannot open `index.html`: the following error is triggered\n" + str(e)
        else:
            break

    # We only deal with PDF file
    download_dir = os.path.join(task_dir, "download")
    shutil.rmtree(download_dir, ignore_errors=True)
    os.makedirs(download_dir, exist_ok=True)
    download_files = []

    fail_obs = ""  # When error execute the action
    pdf_obs = ""  # When download PDF file
    warn_obs = ""  # Type warning
    # alert_obs = ""
    pattern = r'Thought:|Action:|Observation:'

    messages = [{'role': 'system', 'content': OURS_INITIAL_PROMPT}]
    if is_image:
        messages.append({'role': 'user', 'content': [
            {'type': 'text', 'text': f"Website high-level goal: {goal}\nInstructions to verify: as in the image"},
            {'type': 'image_url', 'image_url': instructions},
        ]})
        init_msg = ''
    else:
        init_msg = "Website high-level goal: {}\nInstructions to verify: {}".format(goal, instructions)

    it = 0
    gpt_4v_res = ''
    visuals = None
    last_step = False
    rects_cache = {}
    while it <= max_iter:
        logging.info(f'Iter: {it}')
        it += 1

        if last_step:
            messages += [{'role': 'user', 'content': OURS_LAST_MSG}]

        elif visuals is not None:  # <- visual inspection, only append images in the message
            messages += format_visual_msg(visuals)
            visuals = None

        elif not fail_obs:
            img_path_raw = os.path.join(task_dir, 'screenshot{}_raw.png'.format(it))
            driver_task.save_screenshot(img_path_raw)

            try:
                rects, web_eles, web_eles_text = get_web_element_rect(driver_task, fix_color=False)
                rects_cache[it] = [rect.rect for rect in rects]
            except Exception as e:
                logging.error('Driver error when adding set-of-mark.')
                logging.error(e)
                last_step = True
                messages += [{'role': 'user', 'content': OURS_LAST_MSG}]

            if not last_step:
                img_path = os.path.join(task_dir, 'screenshot{}.png'.format(it))
                driver_task.save_screenshot(img_path)
                if image_width != window_width or image_height != window_height:
                    Image.open(img_path).resize((image_width, image_height)).save(img_path)
                    # <- only resize down annotated screenshot

                # accessibility tree
                accessibility_tree_path = os.path.join(task_dir, 'accessibility_tree{}'.format(it))
                get_webarena_accessibility_tree(driver_task, accessibility_tree_path)

                # encode image
                b64_img = encode_image(img_path)

                # format msg
                if it == max_iter:
                    messages += [{'role': 'user', 'content': OURS_LAST_MSG}]
                    # safeguard: small models won't be able to read BOTH instructions, so we ONLY provide last msg
                    last_step = True
                else:
                    messages += format_msg(it, init_msg, pdf_obs, alert_obs, warn_obs, b64_img, web_eles_text, None)

        else:
            curr_msg = {
                'role': 'user',
                'content': fail_obs
            }
            if it >= max_iter:
                curr_msg['content'] = OURS_LAST_MSG
                last_step = True
            messages.append(curr_msg)

        # Clip messages, too many attached images may cause confusion
        messages = clip_message_and_obs(messages, max_attached_imgs)

        # Call GPT-4v API
        gpt_4v_res = request(messages=messages, **request_kwargs)
        messages.append({'role': 'assistant', 'content': gpt_4v_res})
        if last_step:
            break

        # remove the rects on the website
        if rects:
            logging.info(f"Num of interactive elements: {len(rects)}")
            for rect_ele in rects:
                driver_execute_script_safe(driver_task, "arguments[0].remove()", rect_ele)
            rects = []

        # extract action info
        try:
            assert 'Thought:' in gpt_4v_res and 'Action:' in gpt_4v_res
        except AssertionError as e:
            logging.error(e)
            fail_obs = "Format ERROR: Both 'Thought' and 'Action' should be included in your reply."
            continue

        chosen_action = re.split(pattern, gpt_4v_res)[2].strip()
        action_key, info = extract_information(chosen_action)

        fail_obs = ""
        pdf_obs = ""
        warn_obs = ""
        # execute action
        try:
            if action_key == 'answer' or 'answer; pass' in gpt_4v_res.lower() or 'answer; fail' in gpt_4v_res.lower():
                # "Answer" actions
                logging.info(info['content'])
                logging.info('finish!!')
                last_step = True

            # Below two: visual inspection events, not going to interact with the browser
            elif action_key == 'viewraw':
                i = int(info['content'].split('_')[-1])
                visuals = {'': {
                    'name': f'Raw screenshot_{i}',
                    'b64': encode_image(os.path.join(task_dir, 'screenshot{}_raw.png'.format(i)))
                }}

            elif action_key == 'compare':
                ele_num = int(info['number'])
                i, j = int(info['content'][0]), int(info['content'][1])
                if i == j:
                    fail_obs = ('You need to compare two **different** screenshots; '
                                'instead you compared screenshot_{} and screenshot_{}').format(i, j)
                else:
                    img_i = crop_screenshot_for_rect(os.path.join(task_dir, f"screenshot{i}_raw.png"),
                                                     rects_cache[i][ele_num])
                    img_j = crop_screenshot_for_rect(os.path.join(task_dir, f"screenshot{j}_raw.png"),
                                                     rects_cache[j][ele_num])
                    img = merge_images([img_i, img_j])
                    img.save(os.path.join(task_dir, "screenshot{}.png".format(it + 1)))
                    visuals = {'': {
                        'name': 'Component [{}] from screenshot {} and {}'.format(ele_num, j, i),
                        'b64': encode_pil_image(img)
                    }}

            elif action_key == 'viewanimation':
                i_window = int(info['content'].split('_')[-1])
                image_files = [os.path.join(task_dir, f'screenshot_animation-{i_window}_{i + 1}.png') for i in range(9)]
                if info['number'] == 'WINDOW':
                    images = [Image.open(fn) for fn in image_files]
                    name = "Animation when loading screenshot {}".format(i_window)
                else:
                    ele_num = int(info['number'])
                    images = [crop_screenshot_for_rect(fn, rects_cache[i_window][ele_num]) for fn in image_files]
                    name = "Animation for element [{}] when loading screenshot {}".format(ele_num, i_window)
                image_merged = merge_images(images, nrow=3, ncol=3)
                image_merged = thumbnail_by_max_pixels(image_merged, image_width * image_height)
                image_merged.save(os.path.join(task_dir, "screenshot{}.png".format(it + 1)))
                visuals = {'': {'name': name, 'b64': encode_pil_image(image_merged)}}

            else:  # Below: all browser actions
                window_handle_task = driver_task.current_window_handle
                driver_task.switch_to.window(window_handle_task)

                if action_key == 'click':
                    click_ele_number = int(info[0])
                    web_ele = web_eles[click_ele_number]
                    exec_action_click(info, web_ele, driver_task)

                elif action_key == 'hover':
                    click_ele_number = int(info[0])
                    web_ele = web_eles[click_ele_number]
                    ActionChains(driver_task).move_to_element(web_ele).perform()

                elif action_key == 'type':
                    type_ele_number = int(info['number'])
                    web_ele = web_eles[type_ele_number]
                    warn_obs = exec_action_type(info, web_ele, driver_task)

                elif action_key == 'scroll':
                    exec_action_scroll(info, web_eles, driver_task, None, window_height, text_only=text_only)

                elif action_key == 'goback':
                    driver_task.back()

                elif action_key == 'upload':
                    type_ele_number = int(info['number'])
                    web_ele = web_eles[type_ele_number]
                    warn_obs2 = exec_action_upload(info, web_ele, driver_task)
                    if warn_obs2:
                        warn_obs = warn_obs + '\n' + warn_obs2

                elif action_key == 'select':
                    type_ele_number = int(info['number'])
                    web_ele = web_eles[type_ele_number]
                    warn_obs = exec_action_select(info, web_ele, driver_task)

                else:
                    raise NotImplementedError("{} isn't implemented".format(action_key))

                alert_obs = save_transition_video(driver_task, task_dir, it + 1)

                # deal with download file
                current_files = sorted(os.listdir(download_dir))
                if current_files != download_files:
                    # wait for download finish
                    time.sleep(10)
                    current_files = sorted(os.listdir(download_dir))
                    current_download_files = [filename for filename in current_files if filename not in download_files]
                    pdf_obs = "You have downloaded the following files: " + ", ".join(current_download_files)
                    for filename in current_download_files:
                        if filename.endswith('.pdf'):
                            pdf_obs += "\n\n# Content of {}\n{}\n\n".format(
                                filename, extract_text_from_pdf(os.path.join(download_dir, filename))
                            )
                    pdf_obs = pdf_obs.strip()
                    download_files = current_files

        except Exception as e:
            logging.error('driver error info:')
            logging.error(e)
            if 'element click intercepted' not in str(e):
                fail_obs = "The action you have chosen cannot be executed. Please double-check if you have selected the wrong Numerical Label or Action or Action format. Then provide the revised Thought and Action."
            else:
                fail_obs = ""
            time.sleep(2)

    print_message(messages, task_dir)
    driver_task.quit()
    cleanup_transition_video(task_dir)
    reason = gpt_4v_res.split('ANSWER;')[0].strip().split('Answer;')[0].strip().split("Action:")[0].strip(). \
        replace("Thought:", "").strip()
    can_pass = 'answer; pass' in gpt_4v_res.lower() or any(
        ['answer; pass' in m['content'].lower() for m in messages if m['role'] == 'assistant']
    )
    return can_pass, reason
