import glob
import json
import logging
import os
import re
import shutil
import time

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from utils import encode_image, request, encode_pil_image
from .run import (
    get_default_driver, exec_action_click, exec_action_type, exec_action_scroll, exec_action_select
)
from .utils import (
    driver_get_safe, driver_execute_script_safe, get_web_element_rect, extract_information,
    get_webarena_accessibility_tree, print_message, extract_text_from_pdf
)

with open(os.path.join(os.path.dirname(__file__), 'evaluator_prompts.md')) as f:
    PASS_RATE_EVALUATION_PROMPT = f.read()
PASS_RATE_LAST_MSG = "---\n\nYou've reached the step limit for interacting with the website. Your next action must be ANSWER. Please make your best judgment based on the information so far."

with open(os.path.join(os.path.dirname(__file__), 'usability_evaluator.md')) as f:
    USABILITY_EVALUATION_PROMPT = f.read()
USABILITY_LAST_MSG = "---\n\nYou've reached the step limit for interacting with the website. Please summarize your experience, focusing on the usability of the website."

with open(os.path.join(os.path.dirname(__file__), 'usability_comparison.md')) as f:
    USABILITY_COMPARISON_PROMPT = f.read()


def setup_logger(folder_path):
    log_file_path = os.path.join(folder_path, 'agent.log')

    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    handler = logging.FileHandler(log_file_path)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def format_msg(it, init_msg, pdf_obs, alert_obs, warn_obs, web_img_b64, web_text, last_message, screenshot_name=True):
    if alert_obs:
        web_text = "Pop-up message (already closed): {}\n{}".format(alert_obs, web_text)
    if pdf_obs:
        warn_obs = warn_obs + '\n' + pdf_obs
    if warn_obs:
        web_text = "Observation: {}\n{}".format(warn_obs, web_text)

    msg = "### Textual representation\n"
    if screenshot_name:
        msg += f"Screenshot name: screenshot_{it}\n"
    msg += web_text
    if it == 1:
        msg = (init_msg.strip() + '\n\n' + msg.strip()).strip()
    if last_message is not None:
        msg = msg.strip() + '\n\n' + last_message

    messages = [{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': msg},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{web_img_b64}"}},
        ]
    }, ]
    return messages


def format_visual_msg(visuals):
    messages = [{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': visuals[key]['name']},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{visuals[key]['b64']}"}},
        ]
    } for key in sorted(visuals.keys())]
    return messages


def clip_message_and_obs(msg, max_img_num):
    clipped_msg = []
    img_num = 0

    def clip_image(content):
        nonlocal img_num
        img_num += 1
        if img_num > max_img_num:
            return content[0]['text'] + "\n\n### Image\n(Omitted)"
        else:
            return content

    for idx in range(len(msg)):
        curr_msg = msg[len(msg) - 1 - idx]
        if curr_msg['role'] != 'user':
            clipped_msg = [curr_msg] + clipped_msg
        else:
            if type(curr_msg['content']) != str:
                assert len(curr_msg['content']) == 2
                assert curr_msg['content'][0]['type'] == 'text' and curr_msg['content'][1]['type'] == 'image_url'
                curr_msg['content'] = clip_image(curr_msg['content'])
            clipped_msg = [curr_msg] + clipped_msg
    return clipped_msg


def setup_task_driver(task_dir, url, window_width, window_height):
    driver_task = get_default_driver(tmp_path=task_dir)

    # About window size, 765 tokens
    # You can resize to height = 512 by yourself (255 tokens, Maybe bad performance)
    driver_task.set_window_size(window_width, window_height)  # larger height may contain more web information
    success = driver_get_safe(driver_task, url)
    assert success
    try:  # just quickly abort the alert
        alert = driver_task.switch_to.alert
        alert.accept()
    except NoAlertPresentException:
        pass

    driver_task.refresh()
    try:  # just quickly abort the alert
        alert = driver_task.switch_to.alert
        alert.accept()
    except NoAlertPresentException:
        pass
    alert_obs = save_transition_video(driver_task, task_dir, 1)

    try:
        driver_task.find_element(By.TAG_NAME, 'body').click()
        time.sleep(1)
        driver_execute_script_safe(driver_task, "return 1;")  # no-op, flushing some errors...
        time.sleep(1)
    except Exception as e:
        logging.error(f"Error while clicking body: {e}")
        pass
    # sometimes enter SPACE, the page will sroll down
    driver_execute_script_safe(
        driver_task,
        """window.onkeydown = function(e) {if(e.keyCode == 32 && e.target.type != 'text' && e.target.type != 'textarea') {e.preventDefault();}};"""
    )
    time.sleep(5)

    return driver_task, alert_obs


def exec_action_upload(info, web_ele, driver_task):
    filenames = []
    non_exist = []
    valid_files = ['placeholder.png', 'placeholder.mp3', 'placeholder.mp4', 'placeholder.pdf']
    for fn in info['content']:
        if fn in valid_files:
            fn = os.path.abspath(os.path.join(os.path.dirname(__file__), '../placeholder', fn))
            assert os.path.exists(fn)
            filenames.append(fn)
        else:
            non_exist.append(fn)
    if non_exist:
        return "Files {} don't exist. Please choose between {}. Nothing is uploaded".format(
            ', '.join(non_exist), ', '.join(valid_files)
        )
    web_ele.send_keys("\n".join(filenames))
    return ''


def crop_screenshot_for_rect(filename, rect):
    screenshot = Image.open(filename)
    img_w, img_h = screenshot.size
    # Original rectangle values
    x, y, w, h = int(rect['x']), int(rect['y']), int(rect['width']), int(rect['height'])
    # Double size, keep original in the center
    new_w, new_h = 2 * w, 2 * h
    new_x = x - (new_w - w) // 2
    new_y = y - (new_h - h) // 2
    # Clamp coordinates within image bounds
    left = max(0, new_x)
    top = max(0, new_y)
    right = min(img_w, new_x + new_w)
    bottom = min(img_h, new_y + new_h)
    return screenshot.crop((left, top, right, bottom))


def merge_images(images, nrow=1, ncol=None, pad_percentage=5, bg_color=(255, 255, 255)):
    # Ensure all images are RGB
    images = [img.convert("RGB") for img in images]
    if ncol is None:
        assert len(images) % nrow == 0
        ncol = len(images) // nrow
    else:
        assert len(images) == nrow * ncol

    # Compute max width and height per cell
    cell_width = max(img.width for img in images)
    cell_height = max(img.height for img in images)
    pad = max(cell_width, cell_height) * pad_percentage // 100

    # Compute new image size
    total_width = ncol * cell_width + (ncol - 1) * pad
    total_height = nrow * cell_height + (nrow - 1) * pad
    new_img = Image.new("RGB", (total_width, total_height), bg_color)

    # Paste images into the grid
    for idx, img in enumerate(images):
        row, col = divmod(idx, ncol)
        x = col * (cell_width + pad)
        y = row * (cell_height + pad)
        # Center image within its cell
        x_offset = x + (cell_width - img.width) // 2
        y_offset = y + (cell_height - img.height) // 2
        new_img.paste(img, (x_offset, y_offset))

    return new_img


def save_transition_video(driver, task_dir, it, n_frames=9, interval=0.4):
    alert_obs = ''
    try:  # check alert observation BEFORE saving transition
        alert = driver.switch_to.alert
        alert_obs = alert.text  # optional, to log
        alert.accept()  # or alert.dismiss()
    except NoAlertPresentException:
        pass  # no alert, safe to continue

    save_prefix = os.path.join(task_dir, f'screenshot_animation-{it}')
    for i in range(n_frames):
        time.sleep(interval)
        driver.save_screenshot(save_prefix + "_{}.png".format(i + 1))

    return alert_obs


def cleanup_transition_video(task_dir):
    for file_path in glob.glob(os.path.join(task_dir, 'screenshot_animation-*_*.png')):
        try:
            os.remove(file_path)
        except Exception as e:
            pass


def thumbnail_by_max_pixels(img, max_pixels):
    w, h = img.size
    current_pixels = w * h
    if current_pixels <= max_pixels:
        return img  # no resizing needed

    scale = (max_pixels / current_pixels) ** 0.5
    new_size = (int(w * scale), int(h * scale))

    img_copy = img.copy()
    img_copy.thumbnail(new_size, Image.LANCZOS)
    return img_copy


def run_evaluate(
        url, test_conditions, context, request_kwargs: dict,
        window_width=2048, window_height=1536, image_width=1024, image_height=768,
        max_iter=15, max_attached_imgs=6, text_only=False, fix_box_color=False,
        task_dir=os.path.join(os.environ.get('HOME', './outputs'), "tmp/webvoyager_tmp"),
):
    assert text_only is False
    assert fix_box_color is False

    os.makedirs(task_dir, exist_ok=True)
    setup_logger(task_dir)

    try:
        driver_task, alert_obs = setup_task_driver(task_dir, url, window_width, window_height)
    except:
        return 0

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

    messages = [{'role': 'system', 'content': PASS_RATE_EVALUATION_PROMPT}]
    init_msg = "Test condition: {}\nPass criteria: {}\nFail criteria: {}\n\n### Instructions for Building the Website\n\nUse the following content **only as context** to help understand the website. They **MAY NOT** align with the actual website structure. **Always** rely on **real interactions** with the website to make the final evaluation.\n\n{}".format(
        test_conditions['condition'], test_conditions['pass'], test_conditions['fail'], context
    )

    it = 0
    ret = False
    visuals = None
    rects_cache = {}
    while it <= max_iter:
        logging.info(f'Iter: {it}')
        it += 1

        if visuals is not None:  # <- visual inspection, only append images in the message
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
                break

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
            curr_msg = format_msg(it, init_msg, pdf_obs, alert_obs, warn_obs, b64_img, web_eles_text,
                                  PASS_RATE_LAST_MSG if it == max_iter else None)
            messages += curr_msg

        else:
            curr_msg = {
                'role': 'user',
                'content': fail_obs
            }
            if it >= max_iter:
                curr_msg['content'] = fail_obs.strip() + '\n\n' + PASS_RATE_LAST_MSG
            messages.append(curr_msg)

        # Clip messages, too many attached images may cause confusion
        messages = clip_message_and_obs(messages, max_attached_imgs)

        # Call GPT-4v API
        gpt_4v_res = request(messages=messages, **request_kwargs)
        messages.append({'role': 'assistant', 'content': gpt_4v_res})

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
            if action_key == 'answer':  # "Answer" actions
                logging.info(info['content'])
                logging.info('finish!!')
                ret = info['content'].lower() == 'pass'
                break
            # - sometimes the text isn't in very good form
            elif 'answer; pass' in gpt_4v_res.lower():
                ret = True
                break
            # - sometimes the text isn't in very good form
            elif 'answer; fail' in gpt_4v_res.lower():
                ret = False
                break

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
    return ret


def run_evaluate_usability(
        url, goal, request_kwargs: dict,
        window_width=2048, window_height=1536, image_width=1024, image_height=768,
        max_iter=15, max_attached_imgs=6, text_only=False, fix_box_color=False,
        task_dir=os.path.join(os.environ.get('HOME', './outputs'), "tmp/webvoyager_tmp"),
):
    assert text_only is False
    assert fix_box_color is False

    os.makedirs(task_dir, exist_ok=True)
    setup_logger(task_dir)

    driver_task, alert_obs = setup_task_driver(
        task_dir, url, window_width, window_height
    )  # <- don't do safe any more LOL

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

    messages = [{'role': 'system', 'content': USABILITY_EVALUATION_PROMPT}]
    init_msg = "Website high-level goal: " + goal

    it = 0
    broken = False
    while True:
        logging.info(f'Iter: {it}')
        it += 1

        if not fail_obs:
            img_path_raw = os.path.join(task_dir, 'screenshot{}_raw.png'.format(it))
            driver_task.save_screenshot(img_path_raw)

            try:
                rects, web_eles, web_eles_text = get_web_element_rect(driver_task, fix_color=False)
            except Exception as e:
                logging.error('Driver error when adding set-of-mark.')
                logging.error(e)
                broken = True
                messages.append({'role': 'user', 'content': USABILITY_LAST_MSG})

            if not broken:
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
                curr_msg = format_msg(it, init_msg, pdf_obs, alert_obs, warn_obs, b64_img, web_eles_text,
                                      USABILITY_LAST_MSG if it == max_iter else None, screenshot_name=False)
                messages += curr_msg

        else:
            curr_msg = {
                'role': 'user',
                'content': fail_obs
            }
            if it >= max_iter:
                curr_msg['content'] = fail_obs.strip() + '\n\n' + USABILITY_LAST_MSG
            messages.append(curr_msg)

        # Clip messages, too many attached images may cause confusion
        messages = clip_message_and_obs(messages, max_attached_imgs)

        # Call GPT-4v API
        gpt_4v_res = request(messages=messages, **request_kwargs)
        messages.append({'role': 'assistant', 'content': gpt_4v_res})
        if broken or it >= max_iter:
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


def compare_usability(dA, dB, request_kwargs, max_steps=15):
    def merge_trajectory_images(task_dir):
        images = []
        for i in range(1, max_steps + 1):
            if os.path.exists(os.path.join(task_dir, f'screenshot{i}.png')):
                images.append([f'Step {i}', os.path.join(task_dir, f'screenshot{i}.png'), ])
        if len(images) == 0:
            return None
        if len(images) == 1:
            return images[0][-1]

        ncol = int(np.sqrt(len(images)))
        nrow = int(np.ceil(len(images) / ncol))

        # Create a figure and a grid of subplots (axes)
        # figsize is in inches, you can adjust it to change the overall size
        fig, axes = plt.subplots(nrow, ncol, figsize=(ncol * 4, nrow * 3.5))

        # Flatten the axes array for easy iteration
        axes = axes.flatten()

        # Loop through the images and plot them on the axes
        for i, (title, img_path) in enumerate(images):
            ax = axes[i]
            # Read the image file
            img = plt.imread(img_path)
            ax.imshow(img)
            # Set the title with a larger font size (no font path needed!)
            ax.set_title(title, fontsize=16, pad=10)
            # Turn off the axis ticks and labels for a cleaner look
            ax.axis('off')

        # Turn off any unused subplots at the end of the grid
        for i in range(len(images), len(axes)):
            axes[i].axis('off')

        # Adjust layout to prevent titles from overlapping images
        plt.tight_layout()

        # Save the final figure
        output_filename = os.path.join(task_dir, "merged_screenshots.png")
        plt.savefig(output_filename, bbox_inches='tight', dpi=300)
        return output_filename

    def trajectory_message(dir, traj_id):
        with open(os.path.join(dir, 'interact_messages.json')) as f:
            messages = json.load(f)
        trajectory_text = f'# Trajectory {traj_id}\n\n'
        for i, m in enumerate(messages):
            if m['role'] == 'user':
                if isinstance(m['content'], list):
                    content = m['content'][0]['text']
                else:
                    content = m['content'].replace("### Image\n(Omitted)", "").strip()
                trajectory_text += "## Step {} - Observation\n\n{}\n\n".format(i + 1, content)
            elif m['role'] == 'assistant':
                trajectory_text += "## Step {} - User\n\n{}\n\n".format(i + 1, m['content'])
        content = [{'type': 'text', 'text': trajectory_text}, ]

        trajectory_image = merge_trajectory_images(dir)
        if trajectory_image is not None:
            content.append({
                'type': 'image_url',
                "image_url": {"url": "data:image/png;base64,{}".format(encode_image(trajectory_image))}
            })
        return {'role': 'user', 'content': content}

    trajA = trajectory_message(dA, 'A')
    trajB = trajectory_message(dB, 'B')
    messages = [{'role': 'system', 'content': USABILITY_COMPARISON_PROMPT}, trajA, trajB]

    response = request(messages=messages, **request_kwargs)
    if 'VERDICT:' in response.upper():
        verdict = response.upper().split('VERDICT:')[-1].strip().split()[0]
        verdict_score = {'WIN': 1, 'LOSE': 0, 'TIE': 0.5}.get(verdict, None)
        return response, verdict_score
    else:
        return response, None
