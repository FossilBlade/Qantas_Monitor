from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import shutil
from selenium.common.exceptions import TimeoutException
import sys

from time import sleep
from bs4 import BeautifulSoup
from traceback import print_exc

import json
import datetime

import pandas as pd

from config import routes, schedule_range, close_chrome_after_complete

############### DO NOT REMOVE BELOW ####################################
import chromedriver_binary  # Adds chromedriver binary to path

page_load_timeout = 45

START_URL = 'https://www.qantas.com/au/en/book-a-trip/flights.html'


driver = None
userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36'


def write_to_excel(excel_path, data_list, column_list):
    print('Creating Excel at :'+ os.path.abspath(excel_path))

    prevlen = len(data_list[0])
    for data in data_list:
        if prevlen!=len(data):
            print("LENGTH NOT SAME")

        prevlen=len(data)

    df = pd.pandas.DataFrame.from_dict(data_list, dtype=str)
    writer = pd.ExcelWriter(excel_path, engine='xlsxwriter',options={'strings_to_urls': False})
    df.to_excel(writer,columns=column_list)
    writer.close()



def setup_driver(headless=True):
    global driver

    if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
        shutil.rmtree('chrome-profile')

    options = webdriver.ChromeOptions()
    options.add_argument('--profile-directory=Default')
    options.add_argument("--user-data-dir=chrome-profile/profile")

    options.add_argument("disable-infobars")
    options.add_argument("disable-extensions")
    options.add_argument("disable-cache")
    options.add_argument("disk-cache-size=1")

    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)

    prefs = {'profile.default_content_setting_values': {'cookies': 1, 'images': 2, 'javascript': 1,
                                                        'plugins': 2, 'popups': 2, 'geolocation': 2,
                                                        'notifications': 2, 'auto_select_certificate': 2,
                                                        'fullscreen': 2,
                                                        'mouselock': 2, 'mixed_script': 2, 'media_stream': 2,
                                                        'media_stream_mic': 2, 'media_stream_camera': 2,
                                                        'protocol_handlers': 2,
                                                        'ppapi_broker': 2, 'automatic_downloads': 2, 'midi_sysex': 2,
                                                        'push_messaging': 2, 'ssl_cert_decisions': 2,
                                                        'metro_switch_to_desktop': 2,
                                                        'protected_media_identifier': 2, 'app_banner': 2,
                                                        'site_engagement': 2,
                                                        'durable_storage': 2}}

    options.add_experimental_option("prefs", prefs)

    if headless:
        options.headless = True
        # options.add_argument('--headless')
        options.add_argument('--start-maximized')
        options.add_argument(f'user-agent={userAgent}')
        driver = webdriver.Chrome(options=options, desired_capabilities=None)
        return

    driver = webdriver.Chrome(options=options, desired_capabilities=None)
    driver.set_page_load_timeout(page_load_timeout)
    # driver.set_window_size(1920,1080)

    # # driver.maximize_window()
    # size = driver.get_window_size()
    # driver.set_window_size(size.get('width')/4, size.get('height'))
    # driver.set_window_position(2000, 0)



def click_on_date(date):
    day = int(date.split("-")[0])
    mon = datetime.date(1900, int(date.split("-")[1]), 1).strftime('%B').upper()
    year = int(date.split("-")[2])

    tables = driver.find_elements_by_xpath(
        '//div[@class="date-picker__calendar-container"]//table[@class="date-picker__calendar-table"]')

    correct_mon_found = False
    for table in tables:

        input_mon_year = "{} {}".format(mon, year)
        display_st = table.text.strip()
        if input_mon_year in display_st:
            correct_mon_found = True
            display_day = table.find_element_by_xpath(
                            './/span[@class="date-picker__calendar-weekdays-items-text" and text()="{}"]'.format(day))
            display_day.click()
            # driver.execute_script("arguments[0].click();", display_day)
            break


    if correct_mon_found ==False:
        print('Date {} not found. Moving to next Slot'.format(date))
        driver.find_element_by_css_selector('.date-picker__arrow.date-picker__arrow-right.qfa1-arrow-icon').click()

        tables = driver.find_elements_by_xpath(
            '//div[@class="date-picker__calendar-container"]//table[@class="date-picker__calendar-table"]')

        correct_mon_found = False
        for table in tables:

            input_mon_year = "{} {}".format(mon, year)
            display_st = table.text.strip()
            if input_mon_year in display_st:
                correct_mon_found = True
                display_day = table.find_element_by_xpath(
                    './/span[@class="date-picker__calendar-weekdays-items-text" and text()="{}"]'.format(day))
                display_day.click()
                # driver.execute_script("arguments[0].click();", display_day)
                break

        if correct_mon_found == False:
            raise Exception('Date {} not found.'.format(date))




def login(route, date, counter=0):
    print('Searching for Route [{}] for Date [{}] on page: {} '.format(route,date,START_URL))
    driver.get(START_URL)

    if counter == 0:

        try:

            oneway = driver.find_element_by_xpath('//*[@id="oneway"]')
            driver.execute_script("arguments[0].click();", oneway)
        except:
            driver.save_screenshot("screenshot.png")
            raise

        # sleep(.5)

        src_code = route.split('-')[0]
        src_input = driver.find_element_by_xpath('//input[@id="typeahead-input-from"]')
        src_input.send_keys(Keys.CONTROL + "a")
        src_input.send_keys(Keys.DELETE)
        src_input.send_keys(src_code)
        # sleep(.1)
        src_opt = driver.find_element_by_xpath(
            '//*[@id="typeahead-list-item-from-list"]//strong[text()="{}"]'.format(src_code))
        src_opt.click()

        dest_code = route.split('-')[1]
        dest_input = driver.find_element_by_xpath('//input[@id="typeahead-input-to"]')
        dest_input.send_keys(Keys.CONTROL + "a")
        dest_input.send_keys(Keys.DELETE)
        dest_input.send_keys(dest_code)
        sleep(.1)
        dest_opt = driver.find_element_by_xpath(
            '//*[@id="typeahead-list-item-to-list"]//strong[text()="{}"]'.format(dest_code))
        dest_opt.click()

    date_picker = driver.find_element_by_xpath('//*[@id="datepicker-input-departureDate"]')
    date_picker.click()
    sleep(.3)

    click_on_date(date)
    sleep(.1)

    driver.find_element_by_xpath('//button[text()="SEARCH FLIGHTS"]').click()

    WebDriverWait(driver, 8).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="upsell-container-bound0"]')))

    body = driver.find_element_by_xpath('//*[@id="upsell-container-bound0"]')

    body_html = body.get_attribute("outerHTML")

    with open('temp.html', 'w') as f:
        f.write(body_html)


def read_data(date):
    results = []

    body_html = None
    with open('temp.html', 'r') as f:
        body_html = f.read(body_html)

    soup = BeautifulSoup(body_html, "html.parser")

    sumamry_rows = soup.findAll("upsell-itinerary-avail")

    for row in sumamry_rows:

        flight_detail = {'date': date, 'src': None, 'src_time': None, 'dst': None, 'dst_time': None, 'red_e-deal': None,
                         'flex': None, 'business': None, 'business_classic_reward': None,
                         'economy_classic_reward': None, 'stops': 0, 'f_no': None}

        segments = row.findAll("div", {"class": "segment ng-star-inserted"})

        src_lable = segments[0].find("span", {"class": "textual-label"})
        src = src_lable.getText().strip()
        src_time_span = segments[0].find("span", {"class": "sr-only"})
        src_time = src_time_span.getText().strip()

        dst_lables = segments[-1].findAll("span", {"class": "textual-label"})
        dst = dst_lables[-1].getText().strip()
        dst_time_spans = segments[-1].findAll("span", {"class": "sr-only"})
        dst_time = " ".join(dst_time_spans[-1].getText().strip().split())

        flight_no_span = row.find("span", {"class": "e2e-flight-number"})
        flight_no = flight_no_span.getText().strip()

        fare_names = row.findAll("upsell-fare-cell")

        flight_detail.update(
            {'src': src, 'dst': dst, 'src_time': src_time, 'dst_time': dst_time, 'stops': len(segments) - 1,
             'f_no': flight_no})

        results.append(flight_detail)
        print(
            'Flight Number: {} (Stops: {})\n\t {} : {}\n\t {} : {}'.format(flight_no, len(segments) - 1, src, src_time,
                                                                           dst, dst_time))
        for fare in fare_names:
            name = fare.find('span', {'class': 'e2e-fare-name'}).getText().strip()
            amt_span = fare.find('span', {'class': 'amount cash ng-star-inserted'})
            amt = None
            if amt_span:
                amt = amt_span.getText().strip()
            else:
                amt_span_points = fare.find('span', {
                    'class': 'amount reward-fare-cell-container hidden-selected-mobile ng-star-inserted'})

                if amt_span_points:

                    amt = " ".join(amt_span_points.getText().strip().split())
                    if '+' in amt:
                        amt = amt.replace("+", 'Points +')

            fare_final_name = name.lower().replace(" ", '_')
            if fare_final_name == 'starter':
                fare_final_name = 'red_e-deal'
            elif fare_final_name == 'max':
                fare_final_name = 'flex'

            flight_detail.update({fare_final_name: amt})
            print("\t\t{}: {}".format(name, amt))


    return results







def monitor_ticker(routes, start_day, end_day):
    setup_driver()
    counter = 0
    results = []
    errors = []

    dates = [(datetime.date.today() + datetime.timedelta(days=x)).strftime('%d-%m-%Y') for x in range(start_day, end_day)]

    for route in routes:
        for date in dates:

            try:
                login(route, date, counter=counter)
                results.extend(read_data(date))
                counter = 1
            except:
                print(sys.exc_info())
                errors.append({'route':'route','date':date,'exe':sys.exc_info()[0]})


    print(json.dumps(results, indent=2))

    write_to_excel('Qantus_Data.xlsx',results,[ 'f_no','date','stops', 'src', 'src_time', 'dst', 'dst_time', 'red_e-deal',
                         'flex', 'business', 'business_classic_reward',
                         'economy_classic_reward'])


def run(routes:list, start_day:int, end_day:int):
    try:

        monitor_ticker(routes, start_day, end_day)

    except:
        print_exc()
    finally:
        if close_chrome_after_complete:
            global driver
            if driver:
                driver.quit()


if __name__ == '__main__':
    import time
    import config

    start_time = time.time()
    run(config.routes, 0, 10)
    end_time = time.time()
    print("Time to complete: {}".format(end_time - start_time))
