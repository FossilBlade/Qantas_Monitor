from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import shutil
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import DesiredCapabilities
from selenium.webdriver.common.proxy import Proxy, ProxyType
import sys

from time import sleep
from bs4 import BeautifulSoup
from traceback import print_exc

import json
import datetime

import pandas as pd

import random

import concurrent.futures

import multiprocessing

from email_sender import send_mail
from config import email_to_send_report, close_chrome_after_complete, headless, send_email

import logging

log = logging.getLogger(__name__)

############### DO NOT REMOVE BELOW ####################################
import chromedriver_binary  # Adds chromedriver binary to path

page_load_timeout = 45

START_URL = 'https://www.qantas.com/au/en/book-a-trip/flights.html'
user_agent_list = [
    # Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36',

    # Firefox
    # 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/70.0',
    # 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:61.0) Gecko/20100101 Firefox/70.0',
    # 'Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/70.0'
]


def write_to_excel(excel_path, data_list, column_list):
    if data_list == None or len(data_list) == 0:
        print('Data List empty for creating Excel.')
        return

    print('Creating Excel')

    prevlen = len(data_list[0])
    for data in data_list:
        if prevlen != len(data):
            print("LENGTH NOT SAME")
            print(str(prevlen))
            print(str(data))
        prevlen = len(data)

    df = pd.pandas.DataFrame.from_dict(data_list, dtype=str)
    writer = pd.ExcelWriter(excel_path, engine='xlsxwriter', options={'strings_to_urls': False})
    df.to_excel(writer, columns=column_list)
    writer.close()
    print('Excel Created at :' + os.path.abspath(excel_path))


def get_date_range(start_day, end_day):
    return [(datetime.date.today() + datetime.timedelta(days=x)).strftime('%d-%m-%Y') for x in
            range(start_day, end_day)]


class QantasScrapper:

    def __init__(self, date, routes_list, headless=True, close_driver=True):

        self.all_fare_body_htmls = []
        self.first_search_done = False
        self.driver = None
        self.route = None
        self.results = []
        self.errors = []
        self.close_driver = close_driver
        self.headless = headless
        self.routes_list = routes_list
        self.date = date
        self.__setup_driver()

    def log_info(self, msg):
        log.info('[{}/{}] - {}'.format(self.date, self.route, msg))

    def log_exception(self, msg):
        log.error('[{}/{}] - {}'.format(self.date, self.route, msg), exc_info=True)

    def log_error(self, msg):
        log.error('[{}/{}] - {}'.format(self.date, self.route, msg))

    def log_debug(self, msg):
        log.debug('[{}/{}] - {}'.format(self.date, self.route, msg))

    def __del__(self):
        if self.close_driver == True and self.driver:
            self.driver.quit()

    def __setup_driver(self):

        options = webdriver.ChromeOptions()
        options.add_argument('--profile-directory=Default')
        options.add_argument("--user-data-dir=chrome-profile/profile_{}".format(self.date))
        # options.add_argument("--user-data-dir=chrome-profile/profile_{}".format(os.getpid()))

        options.add_argument("disable-infobars")
        options.add_argument("disable-extensions")
        options.add_argument("disable-cache")
        options.add_argument("disk-cache-size=1")

        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)

        options.add_argument(f'user-agent={random.choice(user_agent_list)}')
        options.add_argument('start-maximized')

        prefs = {'profile.default_content_setting_values': {'cookies': 1, 'images': 2, 'javascript': 1,
                                                            'plugins': 2, 'popups': 2, 'geolocation': 2,
                                                            'notifications': 2, 'auto_select_certificate': 2,
                                                            'fullscreen': 2,
                                                            'mouselock': 2, 'mixed_script': 2, 'media_stream': 2,
                                                            'media_stream_mic': 2, 'media_stream_camera': 2,
                                                            'protocol_handlers': 2,
                                                            'ppapi_broker': 2, 'automatic_downloads': 2,
                                                            'midi_sysex': 2,
                                                            'push_messaging': 2, 'ssl_cert_decisions': 2,
                                                            'metro_switch_to_desktop': 2,
                                                            'protected_media_identifier': 2, 'app_banner': 2,
                                                            'site_engagement': 2,
                                                            'durable_storage': 2}}

        options.add_experimental_option("prefs", prefs)

        if self.headless:
            options.headless = True
            # options.add_argument('--headless')
            options.add_argument('start-maximized')

            self.driver = webdriver.Chrome(options=options, desired_capabilities=None)

        else:
            self.driver = webdriver.Chrome(options=options, desired_capabilities=None)

        self.driver.set_page_load_timeout(page_load_timeout)

    def __process_displayed_months(self, day, mon_name, year):
        tables = self.driver.find_elements_by_xpath(
            '//div[@class="date-picker__calendar-container"]//table[@class="date-picker__calendar-table"]')
        displayed_mon_nos = []
        for table in tables:
            input_mon_year = "{} {}".format(mon_name, year)
            display_st = table.text.strip()
            if input_mon_year in display_st:

                display_day = table.find_element_by_xpath(
                    './/span[@class="date-picker__calendar-weekdays-items-text" and text()="{}"]'.format(day))
                # display_day.click()
                self.driver.execute_script("arguments[0].click();", display_day)
                return []
            else:
                dis_mon_ame = display_st[0].upper() + display_st[1:3].lower()
                dis_month_number = datetime.datetime.strptime(dis_mon_ame, '%b').month

                displayed_mon_nos.append(dis_month_number)

        return displayed_mon_nos

    def __click_on_date(self):

        day = int(self.date.split("-")[0])
        mon_no = self.date.split("-")[1]
        mon_name = datetime.date(1900, int(mon_no), 1).strftime('%B').upper()
        year = int(self.date.split("-")[2])

        date_picker = self.driver.find_element_by_xpath('//*[@id="datepicker-input-departureDate"]')
        date_picker.click()
        sleep(.2)

        displayed_mon_nos = self.__process_displayed_months(day, mon_name, year)

        if len(displayed_mon_nos) == 2:
            while len(displayed_mon_nos) != 0:
                next_mon = self.driver.find_element_by_css_selector(
                    '.date-picker__arrow.date-picker__arrow-right.qfa1-arrow-icon')
                self.driver.execute_script("arguments[0].click();", next_mon)
                displayed_mon_nos = self.__process_displayed_months(day, mon_name, year)
                sleep(.5)

    def __click_one_way(self):

        try:
            oneway = self.driver.find_element_by_xpath('//*[@id="oneway"]')
            self.driver.execute_script("arguments[0].click();", oneway)
        except:
            # self.driver.save_screenshot("screenshot1.png")
            try:
                old_form_link = self.driver.find_element_by_xpath(
                    "//p[contains(text(),'still working through the accessibility functionality of this form')]//a")

                self.log_debug('Different view Detected. Try to go to base view.')
                self.driver.get(old_form_link.get_attribute('href'))

                oneway = self.driver.find_element_by_xpath('//*[@id="oneway"]')
                self.driver.execute_script("arguments[0].click();", oneway)
            except:
                self.log_exception('Error Clicking One-Way.')
                # self.driver.save_screenshot("screenshot2.png")
                raise

    def __enter_place_code(self, type):

        if type == 'src':
            place_code = self.route.split('-')[0]
            place_input = self.driver.find_element_by_xpath('//input[@id="typeahead-input-from"]')
            place_input.send_keys(Keys.CONTROL + "a")
            place_input.send_keys(Keys.DELETE)
            place_input.send_keys(place_code)
            sleep(.1)
            place_opt = self.driver.find_element_by_xpath(
                '//*[@id="typeahead-list-item-from-list"]//strong[text()="{}"]'.format(place_code))
            place_opt.click()

        elif type == "dst":
            place_code = self.route.split('-')[1]
            place_input = self.driver.find_element_by_xpath('//input[@id="typeahead-input-to"]')
            place_input.send_keys(Keys.CONTROL + "a")
            place_input.send_keys(Keys.DELETE)
            place_input.send_keys(place_code)
            sleep(.1)
            place_opt = self.driver.find_element_by_xpath(
                '//*[@id="typeahead-list-item-to-list"]//strong[text()="{}"]'.format(place_code))
            place_opt.click()

        else:
            raise Exception('Incorrect Place Type')

    def __click_search(self):
        # sleep(2)

        src_btn = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//button[text()="SEARCH FLIGHTS"]')))
        # self.driver.execute_script("arguments[0].scrollIntoView();", src_btn)
        # src_btn.location_once_scrolled_into_view
        self.driver.execute_script("arguments[0].click();", src_btn)
        # src_btn.click()

        # self.driver.find_element_by_xpath('//button[text()="SEARCH FLIGHTS"]').click()

        try:
            # WebDriverWait(self.driver, 10).until(
            #     EC.presence_of_all_elements_located((By.TAG_NAME, 'upsell-itinerary-avail')))
            # WebDriverWait(self.driver, 10).until(
            #     EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.segment.ng-star-inserted')))

            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.e2e-flight-number')))

            # e2e-flight-number


        except:
            # self.log_exception('First Fare Type not found.')
            raise Exception('First Fare Type not found: {}'.format())
        else:
            body = self.driver.find_element_by_id('upsell-container-bound0')
            body_html = body.get_attribute("outerHTML")
            self.log_info('Processing Base Fare Class')
            self.__save_data(body_html)
            # self.all_fare_body_htmls.append(body_html)

        extra_fare_classes_names = []
        try:
            extra_fare_classes = self.driver.find_elements_by_xpath('//div[@class="cabin-selector-row"]//button')[1:]
        except:
            self.log_info('Other Fare Types not found.')
        else:
            for fare_class in extra_fare_classes:
                extra_fare_classes_names.append(fare_class.text)

        for fare_class_name in extra_fare_classes_names:
            fare_class = self.driver.find_element_by_xpath(
                '//div[@class="cabin-selector-row"]//button[contains(text(),"{}")]'.format(fare_class_name))

            self.log_info('Clicking and processing fare type: {}'.format(fare_class_name))
            fare_class.click()

            # old_list = WebDriverWait(self.driver, 15).until(
            #     EC.presence_of_element_located((By.XPATH,
            #                                     '//div[@class="card-header" or contains(@class,"card-warning")]')))
            old_txt = None

            while True:

                new_list = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    '//div[@class="card-header" or contains(@class,"card-warning")]')))
                new_txt = new_list.text.strip()

                if old_txt != new_txt or "We don’t have any seats available, try another cabin class" in new_txt:

                    break
                else:
                    old_txt = new_txt
                sleep(.5)

            try:
                # WebDriverWait(self.driver, 10).until(
                #     EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.segment.ng-star-inserted')))

                WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.e2e-flight-number')))

            except:
                self.log_info('Itinerary Detail not found for: {}'.format(fare_class_name))

            else:
                body = self.driver.find_element_by_id('upsell-container-bound0')
                body_html = body.get_attribute("outerHTML")
                self.log_info('Processing HTML for {}'.format(fare_class_name))
                self.__save_data(body_html)
                # self.all_fare_body_htmls.append(body_html)

        self.log_info('All fare type found.')

    # def __save_data(self):
    #
    #     self.log_info('Extracting info from HTML.')
    #     for fare_classes_html in self.all_fare_body_htmls:
    #
    #         soup = BeautifulSoup(fare_classes_html, "html.parser")
    #
    #         sumamry_rows = soup.findAll("upsell-itinerary-avail")
    #
    #         for row in sumamry_rows:
    #
    #             flight_detail = {'date': self.date, 'src': None, 'src_time': None, 'dst': None, 'dst_time': None,
    #                              'stops': 0, 'f_no': None,
    #
    #                              'red_e-deal': None, 'flex': None, 'business': None, 'business_classic_reward': None,
    #                              'economy_classic_reward': None, 'sale': None, 'saver': None,
    #                              'premium_economy_sale': None,
    #                              'premium_economy_flex': None, 'first_saver': None,
    #                              'first_flex': None, 'business_saver': None, 'business_flex': None,
    #                              'premium_economy_saver': None, 'business_sale': None,
    #                              'premium_economy_classic_reward': None,'first_classic_reward':None}
    #
    #             segments = row.findAll("div", {"class": "segment ng-star-inserted"})
    #             if len(segments)==0:
    #                 self.log_error("Couldn't find segment: \n{}".format(row.prettify()))
    #                 # print(row.html)
    #                 continue
    #
    #             src_lable = segments[0].find("span", {"class": "textual-label"})
    #             src = src_lable.getText().strip()
    #             src_time_span = segments[0].find("span", {"class": "sr-only"})
    #             src_time = src_time_span.getText().strip()
    #
    #             dst_lables = segments[-1].findAll("span", {"class": "textual-label"})
    #             dst = dst_lables[-1].getText().strip()
    #             dst_time_spans = segments[-1].findAll("span", {"class": "sr-only"})
    #             dst_time = " ".join(dst_time_spans[-1].getText().strip().split())
    #
    #             flight_no_span = row.find("span", {"class": "e2e-flight-number"})
    #             flight_no = flight_no_span.getText().strip()
    #
    #             fare_names = row.findAll("upsell-fare-cell")
    #
    #             flight_detail.update(
    #                 {'src': src, 'dst': dst, 'src_time': src_time, 'dst_time': dst_time, 'stops': len(segments) - 1,
    #                  'f_no': flight_no})
    #
    #             self.results.append(flight_detail)
    #
    #             for fare in fare_names:
    #                 name = fare.find('span', {'class': 'e2e-fare-name'}).getText().strip()
    #                 amt_span = fare.find('span', {'class': 'amount cash ng-star-inserted'})
    #                 amt = None
    #                 if amt_span:
    #                     amt = amt_span.getText().strip()
    #                 else:
    #                     amt_span_points = fare.find('span', {
    #                         'class': 'amount reward-fare-cell-container hidden-selected-mobile ng-star-inserted'})
    #
    #                     if amt_span_points:
    #
    #                         amt = " ".join(amt_span_points.getText().strip().split())
    #                         if '+' in amt:
    #                             amt = amt.replace("+", 'Points +')
    #
    #                 fare_final_name = name.lower().replace(" ", '_')
    #                 if fare_final_name == 'starter':
    #                     fare_final_name = 'red_e-deal'
    #                 elif fare_final_name == 'max':
    #                     fare_final_name = 'flex'
    #
    #                 flight_detail.update({fare_final_name: amt})

    def __save_data(self, fare_classe_html):

        self.log_info('Extracting info from HTML.')

        soup = BeautifulSoup(fare_classe_html, "html.parser")

        sumamry_rows = soup.findAll("upsell-itinerary-avail")

        for row in sumamry_rows:

            flight_detail = {'date': self.date, 'src': None, 'src_time': None, 'dst': None, 'dst_time': None,
                             'stops': 0, 'f_no': None,

                             'red_e-deal': None, 'flex': None, 'business': None, 'business_classic_reward': None,
                             'economy_classic_reward': None, 'sale': None, 'saver': None,
                             'premium_economy_sale': None,
                             'premium_economy_flex': None, 'first_saver': None,
                             'first_flex': None, 'business_saver': None, 'business_flex': None,
                             'premium_economy_saver': None, 'business_sale': None,
                             'premium_economy_classic_reward': None, 'first_classic_reward': None}

            # segments = row.findAll("div", {"class": "segment ng-star-inserted"})
            segments = row.findAll('upsell-segment-details')
            if len(segments) == 0:
                self.log_error("Couldn't find segment(Row Count: {}): \n{}".format(len(sumamry_rows), row.prettify()))
                # print(row.html)
                continue

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

            self.results.append(flight_detail)

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

    def __search(self):

        self.driver.get(START_URL)

        if self.first_search_done == False:
            self.log_debug('Entering DATE, SRC and DST.')
            self.__click_one_way()

            self.__enter_place_code('src')
            self.__enter_place_code('dst')

            self.__click_on_date()
            self.first_search_done = True
        else:
            self.log_debug('Entering SRC and DST Only')
            self.__enter_place_code('src')
            self.__enter_place_code('dst')

        self.__click_search()

        # self.__save_data()

    def loop_over_routes(self):
        for self.route in self.routes_list:

            try:
                self.log_info('Search Started')
                self.__search()
            except:
                self.log_exception('Error Processing.')
                self.errors.append({'route': self.route, 'date': self.date, 'exe': sys.exc_info()[1]})


def scrap(date, routes):
    scrapper = QantasScrapper(date, routes, headless=headless, close_driver=close_chrome_after_complete)
    scrapper.loop_over_routes()
    return scrapper.results, scrapper.errors


def is_job_running():
    if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
        return True
    else:
        return False


def run(routes: list, start_day: int, end_day: int, job_id=0):
    job_id = str(job_id)

    if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
        shutil.rmtree('chrome-profile')

    dates = get_date_range(start_day, end_day)
    routes = list(set(routes))

    final_res = []
    final_ero = []
    # multiprocessing.cpu_count()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        future_to_scrappers = {executor.submit(scrap, date, routes): "{}_{}".format(date, routes) for date in dates}

        for future in concurrent.futures.as_completed(future_to_scrappers):

            date_route = future_to_scrappers[future]

            try:
                data, error = future.result()
            except Exception as exc:
                log.error('%r generated an exception: %s' % (date_route, exc), exc_info=True)
            else:
                final_res.extend(data)
                final_ero.extend(error)

    report_name = 'Qantas_Data_{}.xlsx'.format(job_id)
    error_rep_name = 'Error_Data_{}.xlsx'.format(job_id)
    report_file_path_tmpl = 'db/{}/{}'

    if not os.path.exists(os.path.dirname(report_file_path_tmpl.format(job_id, report_name))):
        # os.makedirs(directory)
        os.makedirs(os.path.dirname(report_file_path_tmpl.format(job_id, report_name)))

    write_to_excel(report_file_path_tmpl.format(job_id, report_name), final_res,
                   ['f_no', 'date', 'stops', 'src', 'src_time', 'dst', 'dst_time', 'red_e-deal',
                    'flex', 'business', 'business_classic_reward',
                    'economy_classic_reward', 'sale', 'saver', 'premium_economy_sale', 'premium_economy_flex',
                    'first_saver', 'first_flex', 'business_saver', 'business_flex', 'premium_economy_saver',
                    'business_sale', 'premium_economy_classic_reward', 'first_classic_reward'])

    write_to_excel(report_file_path_tmpl.format(job_id, error_rep_name), final_ero, ['route', 'date', 'exe'])

    if send_email:
        send_mail(email_to_send_report, job_id, os.path.dirname(report_file_path_tmpl.format(job_id, report_name)))

    if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
        shutil.rmtree('chrome-profile')


if __name__ == '__main__':
    import time

    routes = ['SYD-CAN']  # , 'SYD-MEL'

    start_time = time.time()
    run(routes, 120, 121)
    end_time = time.time()
    print("Time to complete: {}".format(end_time - start_time))
