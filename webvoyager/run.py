import os
import platform

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from .utils import driver_execute_script_safe


def get_default_driver(tmp_path=os.path.join(os.environ.get('HOME', './outputs'), "tmp"),
                       binary_location=os.environ.get('CHROME_BINARY'),
                       service_location=os.environ.get('CHROME_DRIVER')):
    # options
    options = webdriver.ChromeOptions()
    if binary_location is not None:
        options.binary_location = binary_location
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--headless=new")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    )
    options.add_experimental_option(
        "prefs", {
            "download.default_directory": os.path.abspath(os.path.join(tmp_path, "download")),
            "plugins.always_open_pdf_externally": True
        }
    )
    kwargs = dict(options=options)

    if service_location is not None:
        service = Service(service_location)
        kwargs['service'] = service

    # Start headless Chrome
    driver = webdriver.Chrome(**kwargs)
    return driver


def exec_action_click(info, web_ele, driver_task):
    driver_execute_script_safe(driver_task, "arguments[0].setAttribute('target', '_self')", web_ele)
    web_ele.click()
    # time.sleep(3)


def exec_action_type(info, web_ele, driver_task):
    warn_obs = ""
    type_content = info['content']

    ele_tag_name = web_ele.tag_name.lower()
    ele_type = web_ele.get_attribute("type")
    # outer_html = web_ele.get_attribute("outerHTML")
    if (ele_tag_name != 'input' and ele_tag_name != 'textarea') or (
            ele_tag_name == 'input' and ele_type not in ['text', 'search', 'password', 'email', 'tel']):
        warn_obs = f"note: The web element you're trying to type may not be a textbox, and its tag name is <{web_ele.tag_name}>, type is {ele_type}."
    try:
        # Not always work to delete
        web_ele.clear()
        # Another way to delete
        if platform.system() == 'Darwin':
            web_ele.send_keys(Keys.COMMAND + "a")
        else:
            web_ele.send_keys(Keys.CONTROL + "a")
        web_ele.send_keys(" ")
        web_ele.send_keys(Keys.BACKSPACE)
    except:
        pass

    actions = ActionChains(driver_task)
    actions.click(web_ele).perform()
    # actions.pause(1)

    try:
        driver_execute_script_safe(
            driver_task,
            """window.onkeydown = function(e) {if(e.keyCode == 32 && e.target.type != 'text' && e.target.type != 'textarea' && e.target.type != 'search') {e.preventDefault();}};"""
        )
    except:
        pass

    actions.send_keys(type_content)
    # actions.pause(2)
    # actions.send_keys(Keys.ENTER)
    actions.perform()
    # time.sleep(5)
    return warn_obs


def exec_action_select(info, web_ele, driver_task):
    type_content = info['content']

    try:
        select = Select(web_ele)
    except:
        return f"note: The web element you're trying to select from may not be a dropbox, and its tag name is <{web_ele.tag_name}>."

    matched_type_content = None
    for option in select.options:
        if option.text.strip() == type_content.strip():
            matched_type_content = option.text
            break
        if option.text.strip().lower() == type_content.strip().lower():
            matched_type_content = option.text
    if matched_type_content is None:
        return f"note: Your selected option \"{type_content}\" is an invalid option. Valid options are: " + \
            ", ".join([f'"{option.text}"'.format() for option in select.options])

    select.select_by_visible_text(matched_type_content)
    return ''


def exec_action_scroll(info, web_eles, driver_task, obs_info, window_height, text_only=False):
    scroll_ele_number = info['number']
    scroll_content = info['content']
    if scroll_ele_number == "WINDOW":
        if scroll_content == 'down':
            driver_execute_script_safe(driver_task, f"window.scrollBy(0, {window_height * 2 // 3});")
        else:
            driver_execute_script_safe(driver_task, f"window.scrollBy(0, {-window_height * 2 // 3});")
    else:
        if not text_only:
            scroll_ele_number = int(scroll_ele_number)
            web_ele = web_eles[scroll_ele_number]
        else:
            element_box = obs_info[scroll_ele_number]['union_bound']
            element_box_center = (element_box[0] + element_box[2] // 2, element_box[1] + element_box[3] // 2)
            web_ele = driver_execute_script_safe(
                driver_task,
                "return document.elementFromPoint(arguments[0], arguments[1]);",
                element_box_center[0], element_box_center[1]
            )
        actions = ActionChains(driver_task)
        driver_execute_script_safe(driver_task, "arguments[0].focus();", web_ele)
        if scroll_content == 'down':
            actions.key_down(Keys.ALT).send_keys(Keys.ARROW_DOWN).key_up(Keys.ALT).perform()
        else:
            actions.key_down(Keys.ALT).send_keys(Keys.ARROW_UP).key_up(Keys.ALT).perform()
