from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import shutil
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

import sys
from random import shuffle
from time import sleep, time as timestamp
from bs4 import BeautifulSoup

import datetime

import pandas as pd

from email_sender import send_mail
from config import email_to_send_report, close_chrome_after_complete, headless, send_email, parallel_processe_count, \
    print_trace_back, auto_retry_count

import socket

import logging

log = logging.getLogger(__name__)

############### DO NOT REMOVE BELOW ####################################
import chromedriver_binary  # Adds chromedriver binary to path

page_load_timeout = 60

START_URL = 'https://www.qantas.com/au/en/book-a-trip/flights.html'

fare_type_list = ['red_e-deal', 'flex', 'business', 'business_classic_reward',
                  'economy_classic_reward', 'sale', 'saver',
                  'premium_economy_sale',
                  'premium_economy_flex', 'first_saver', 'first_sale',
                  'first_flex', 'business_saver', 'business_flex',
                  'premium_economy_saver', 'business_sale',
                  'premium_economy_classic_reward', 'first_classic_reward']

fare_name_tmpl = '{} Fare'


def get_free_tcp_port():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port


def write_to_excel(excel_path, data_list, error_list, data_column_list, error_column_list):
    if (data_list == None or len(data_list) == 0) and (error_list == None or len(error_list) == 0):
        log.info('No Data for Creating Excel')
        return

    writer = pd.ExcelWriter(excel_path, engine='xlsxwriter', options={'strings_to_urls': False})
    if data_list == None or len(data_list) == 0:
        log.info('Data List empty for creating Excel.')
    else:
        prevlen = len(data_list[0])
        for data in data_list:
            if prevlen != len(data):
                log.warning("LENGTH NOT SAME")
                log.warning(str(prevlen))
                log.warning(str(data))
            prevlen = len(data)
        log.debug('Creating Data Sheet')
        data_df = pd.pandas.DataFrame.from_dict(data_list, dtype=str)
        data_df.to_excel(writer, columns=data_column_list, sheet_name='Result', index=False)

    if error_list == None or len(error_list) == 0:
        log.info('Error List empty for creating Excel.')
    else:

        log.debug('Creating Error Sheet Excel')
        error_df = pd.pandas.DataFrame.from_dict(error_list, dtype=str)
        error_df.to_excel(writer, columns=error_column_list, sheet_name='Errors', index=False)

    writer.close()
    log.info('Excel Created at :' + os.path.abspath(excel_path))


def get_date_range(start_day, end_day):
    return [(datetime.date.today() + datetime.timedelta(days=x)).strftime('%d-%m-%Y') for x in
            range(start_day, end_day)]


class QantasScrapper:

    def __init__(self, date, routes_list, headless=True, close_driver=True, job_id=0):
        self.driver_is_open = False
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
        self.job_id = job_id

    def log_info(self, msg):
        log.info('[{}/{}] - {}'.format(self.date, self.route, msg))

    def log_exception(self, msg):

        log.error('[{}/{}] - {}'.format(self.date, self.route, msg), exc_info=True)

    def log_error(self, msg):
        log.error('[{}/{}] - {}'.format(self.date, self.route, msg))

    def log_warn(self, msg):
        log.warning('[{}/{}] - {}'.format(self.date, self.route, msg))

    def log_debug(self, msg):
        log.debug('[{}/{}] - {}'.format(self.date, self.route, msg))

    def __del__(self):
        self.close_driver_and_delete_profile()

    def __setup_driver(self):

        options = webdriver.ChromeOptions()
        options.add_argument('--profile-directory=Default')
        options.add_argument("--user-data-dir=chrome-profile/profile_{}".format(self.date))

        options.add_argument("disable-infobars")
        options.add_argument("disable-extensions")
        options.add_argument("disable-cache")
        options.add_argument("disk-cache-size=1")
        # options.add_argument("incognito")
        # options.add_argument('lang=en_US')

        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)

        # options.add_argument(f'user-agent={random.choice(user_agent_list)}')
        # options.add_argument('start-maximized')

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
            options.add_argument("remote-debugging-port={}".format(get_free_tcp_port()))
            # options.add_argument('start-maximized')

            self.driver = webdriver.Chrome(options=options, desired_capabilities=None)

        else:
            self.driver = webdriver.Chrome(options=options, desired_capabilities=None)

        self.driver_is_open = True
        # self.driver.minimize_window()
        self.driver.set_page_load_timeout(page_load_timeout)

    def expand_shadow_element(self, element):
        shadow_root = self.driver.execute_script('return arguments[0].shadowRoot', element)
        return shadow_root

    def get_clear_browsing_button(self):
        """Find the "CLEAR BROWSING BUTTON" on the Chrome settings page."""
        # return self.driver.find_element_by_xpath('/html/body/settings-ui//div[2]/settings-main//settings-basic-page//div[3]/settings-section[1]/settings-privacy-page//settings-clear-browsing-data-dialog//cr-dialog/div[4]/cr-button[2]')

        root1 = self.driver.find_element_by_css_selector('settings-ui')
        shadow_root1 = self.expand_shadow_element(root1)

        root2 = shadow_root1.find_element_by_css_selector('settings-main')
        shadow_root2 = self.expand_shadow_element(root2)

        root3 = shadow_root2.find_element_by_css_selector('settings-basic-page')
        shadow_root3 = self.expand_shadow_element(root3)

        root4 = shadow_root3.find_element_by_css_selector('settings-section > settings-privacy-page')
        shadow_root4 = self.expand_shadow_element(root4)

        root5 = shadow_root4.find_element_by_css_selector('settings-clear-browsing-data-dialog')
        shadow_root5 = self.expand_shadow_element(root5)

        root6 = shadow_root5.find_element_by_css_selector('#clearBrowsingDataDialog')
        # shadow_root6 = self.expand_shadow_element(root6)

        # print(self.driver.execute_script("return arguments[0].innerHTML;", shadow_root6))

        search_button = root6.find_element_by_id("clearBrowsingDataConfirm")

        return search_button

    def clear_cache(self, timeout=60):
        self.log_info('Clearing the cookies and cache for the ChromeDriver instance.')
        """"""
        # navigate to the settings page
        self.driver.get('chrome://settings/clearBrowserData')

        self.get_clear_browsing_button().click()

        timeout = 60
        timeout_start = timestamp()

        while self.driver.current_url != 'chrome://settings/':
            if timestamp() > timeout_start + timeout:
                self.log_warn('Timed-out waiting for browser clear history')
                break
            sleep(.5)

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
            try:
                old_form_link = self.driver.find_element_by_xpath(
                    "//p[contains(text(),'still working through the accessibility functionality of this form')]//a")

                self.log_debug('Different view Detected. Try to go to base view.')
                self.driver.get(old_form_link.get_attribute('href'))

                oneway = self.driver.find_element_by_xpath('//*[@id="oneway"]')
                self.driver.execute_script("arguments[0].click();", oneway)
            except:
                raise Exception("Start page did not load properly. Can't find expected elements.")

    def __enter_place_code(self, type):

        clear_btns = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_all_elements_located((By.XPATH, '//div[@class="qfa1-typeahead__close-button"]')))

        if type == 'src':
            place_code = self.route.split('-')[0]
            self.log_debug('Entering SRC: ' + place_code)

            self.driver.execute_script("arguments[0].click();", clear_btns[0])

            place_input = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//input[@id="typeahead-input-from"]')))

            self.send_keys(place_input, place_code,clear_btns[0])

            place_opt = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="typeahead-list-item-from-list"]//strong[text()="{}"]'.format(place_code))))

            place_opt.click()

        elif type == "dst":

            place_code = self.route.split('-')[1]
            self.log_debug('Entering DST: ' + place_code)

            self.driver.execute_script("arguments[0].click();", clear_btns[-1])

            place_input = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//input[@id="typeahead-input-to"]')))

            self.send_keys(place_input, place_code,clear_btns[-1])

            try:
                place_opt = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="typeahead-list-item-to-list"]//strong[text()="{}"]'.format(place_code))))
            except TimeoutException:
                result_opt = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="typeahead-list-item-to-list"]'.format(place_code))))
                if "We can't find a matching location for" in result_opt.text:
                    raise Exception('Invalid Code Used: ' + place_code)
                else:
                    raise

            place_opt.click()

        else:
            raise Exception('Incorrect Place Type')

    def send_keys(self, elem, keys,clear_btn):
        sleep(.1)
        for i in range(len(keys)):
            elem.send_keys(keys[i])
            sleep(.1)

        if elem.get_attribute('value') != keys:
            # elem.clear()
            self.driver.execute_script("arguments[0].click();", clear_btn)
            self.send_keys(elem, keys)

    def __click_search(self):

        src_btn = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//button[text()="SEARCH FLIGHTS"]')))

        self.driver.execute_script("arguments[0].click();", src_btn)

        try:
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.e2e-flight-number')))
        except:

            bound = self.driver.find_element_by_tag_name("body")
            if 'Flights are not available on this date. See other dates above.' in bound.text:
                self.log_warn("No Flights Available for this date and route.")
                return


            elif 'access denied' in bound.text.lower():
                self.clear_cache()
                raise Exception('Access Denied. Will be retried at the end.')


            elif 'please select at least one passenger' in bound.text.lower():
                self.log_warn("Clicking search again as passengers were not set.")

                passen_parent_div = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//label[text()="Passengers"]/..')))

                # print(passen_parent_div.get_attribute("outerHTML"))

                people_input = WebDriverWait(passen_parent_div, 5).until(
                    EC.element_to_be_clickable(
                        (By.TAG_NAME, 'input')))

                people_count = people_input.get_attribute('value')
                self.log_debug('PEOPLE COUNT: ' + people_count)

                self.driver.execute_script("arguments[0].click();", people_input)

                ppl_plus = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@class="qfa1-numberpicker__plus-icon"]')))

                self.driver.execute_script("arguments[0].click();", ppl_plus)

                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@class="qfa1-submit-button__button"]')))

                btn.click()

                self.__click_search()
                return
            else:
                raise Exception('Search Result took more than 30 seconds to load. Will be retried at the end.')
        else:
            body = self.driver.find_element_by_id('upsell-container-bound0')
            body_html = body.get_attribute("outerHTML")
            self.log_debug('Processing First Result Page')
            self.__save_data(body_html)

        extra_fare_classes_names = []
        try:
            extra_fare_classes = self.driver.find_elements_by_xpath('//div[@class="cabin-selector-row"]//button')[1:]
        except:
            self.log_debug('Other Fare Types not found.')
        else:
            for fare_class in extra_fare_classes:
                extra_fare_classes_names.append(fare_class.text)

        for fare_class_name in extra_fare_classes_names:
            fare_class = self.driver.find_element_by_xpath(
                '//div[@class="cabin-selector-row"]//button[contains(text(),"{}")]'.format(fare_class_name))

            old_list = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//div[@class="card-header" or contains(@class,"card-warning")]')))
            old_txt = old_list.text.strip()

            self.log_info('Clicking and processing fare type: {}'.format(fare_class_name))
            fare_class.click()

            timeout = 20
            timeout_start = timestamp()
            while True:
                if timestamp() > timeout_start + timeout:
                    break

                try:
                    new_list = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH,
                                                        '//div[@class="card-header" or contains(@class,"card-warning")]')))
                    new_txt = new_list.text.strip()
                except StaleElementReferenceException as se:
                    sleep(1)
                    continue

                if old_txt != new_txt or "We don’t have any seats available, try another cabin class" in new_txt:
                    break

                sleep(.5)

            try:

                WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.e2e-flight-number')))

            except:
                self.log_info('No seats available for: {}'.format(fare_class_name))

            else:
                body = self.driver.find_element_by_id('upsell-container-bound0')
                body_html = body.get_attribute("outerHTML")
                self.__save_data(body_html)

        self.log_info('All fare type processed.')

    def __save_data(self, fare_classe_html):

        self.log_debug('Extracting info from HTML.')

        soup = BeautifulSoup(fare_classe_html, "html.parser")

        summary_rows = soup.findAll("upsell-itinerary-avail")

        for row in summary_rows:

            flight_detail = {'Date': self.date, 'Departs': None, 'Dep Time': None, 'Arrives': None, 'Arr Time': None,
                             'Stops': 0, 'Flight': None}

            for fare_type in fare_type_list:
                flight_detail.update({fare_name_tmpl.format(fare_type): None})

            segments = row.findAll('upsell-segment-details')
            if len(segments) == 0:
                self.log_debug("Couldn't find segment(Row Count: {}): \n{}".format(len(summary_rows), row.prettify()))
                continue

            src_label = segments[0].find("span", {"class": "textual-label"})
            src = src_label.getText().strip()
            src_time_span = segments[0].find("span", {"class": "sr-only"})
            src_time = src_time_span.getText().strip()

            dst_labels = segments[-1].findAll("span", {"class": "textual-label"})
            dst = dst_labels[-1].getText().strip()
            # dst_time_div_row = segments[-1].findAll("div", {"class": "row"})
            # dst_time_div = dst_time_div_row[-2].findAll("div")[-1]
            # dst_time = " ".join(dst_time_div.getText().strip().split())
            div_arr_dep = segments[-1].find("div", {"class": "departure-arrival-time"})
            dst_time_div = div_arr_dep.find("div", {"class": "text-right"})
            dst_time = " ".join(dst_time_div.getText().strip().split())

            flight_no_span = row.find("span", {"class": "e2e-flight-number"})
            flight_no = flight_no_span.getText().strip()

            fare_names = row.findAll("upsell-fare-cell")

            flight_detail.update(
                {'Departs': src, 'Arrives': dst, 'Dep Time': src_time, 'Arr Time': dst_time, 'Stops': len(segments) - 1,
                 'Flight': flight_no})

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

                flight_detail.update({fare_name_tmpl.format(fare_final_name): amt})

    def __search(self):

        self.log_info('Search Started for {} {}'.format(self.route, self.date))
        self.driver.get(START_URL)

        self.__click_one_way()

        self.__enter_place_code('src')
        self.__enter_place_code('dst')

        self.__click_on_date()

        self.__click_search()

    def loop_over_routes(self):
        for self.route in self.routes_list:

            try:
                self.__search()
            except:
                if 'Invalid Code Used' not in str(sys.exc_info()[1]):
                    self.save_screenshot("db/{}/error/{}_{}_Error.png".format(self.job_id, self.route, self.date))
                if not print_trace_back:
                    self.log_error(sys.exc_info()[1])
                else:
                    self.log_exception('Error Processing')
                self.errors.append({'route': self.route, 'date': self.date, 'exe': str(sys.exc_info()[1])})

        self.close_driver_and_delete_profile()

    def close_driver_and_delete_profile(self):
        if self.close_driver == True and self.driver and self.driver_is_open:
            self.driver.close()
            self.driver_is_open = False

    def save_screenshot(self, path):
        # Ref: https://stackoverflow.com/a/52572919/
        try:
            original_size = self.driver.get_window_size()
            required_width = self.driver.execute_script('return document.body.parentNode.scrollWidth')
            required_height = self.driver.execute_script('return document.body.parentNode.scrollHeight')

            self.driver.set_window_size(required_width, required_height)
            # driver.save_screenshot(path)  # has scrollbar
            self.driver.find_element_by_tag_name('body').screenshot(path)  # avoids scrollbar
            self.driver.set_window_size(original_size['width'], original_size['height'])
        except:

            try:
                self.driver.save_screenshot(path)
            except:
                self.log_warn('Could not take a snapshot of the error page')


def scrap_retry(date, routes, job_id, full_data=[], full_error=[], called_counter=1):
    scrapper = QantasScrapper(date, routes, job_id=job_id, headless=headless, close_driver=close_chrome_after_complete)
    scrapper.loop_over_routes()

    full_data.extend(scrapper.results)

    retry_routes = []
    removed_error = []

    for err in scrapper.errors:
        if 'Invalid Code Used' not in err.get('exe'):
            retry_routes.append(err.get('route'))
            removed_error.append(err)
        else:
            full_error.append(err)

    if called_counter > auto_retry_count:
        full_error.extend(removed_error)
        return

    called_counter += 1

    if len(retry_routes) > 0:
        log.info('##### RETRYING FAILED ROUTES FOR {} : {}'.format(date, retry_routes))
        scrap_retry(date, retry_routes, job_id, full_data=full_data, full_error=full_error,
                    called_counter=called_counter)


def scrap(date, routes, job_id):
    full_data = []
    full_error = []
    scrap_retry(date, routes, job_id, full_data=full_data, full_error=full_error)
    return full_data, full_error


def is_job_running():
    if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
        return True
    else:
        return False


def run(routes: list, start_day: int, end_day: int, job_id=0):
    job_id = str(job_id)

    error_folder = 'db/{}/error'.format(job_id)
    report_name = 'db/{}/Qantas_Data_{}.xlsx'.format(job_id, job_id)

    if not os.path.exists(error_folder):
        os.makedirs(error_folder)

    if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
        shutil.rmtree('chrome-profile')
    log.info('Getting Date range for days: {} - {}'.format(start_day, end_day))
    dates = get_date_range(start_day, end_day)
    # remove duplicates and maintaine order
    routes = list(dict.fromkeys(routes))

    final_res = []
    final_ero = []

    # shuffle(dates)
    # shuffle(routes)

    log.info("Processing following routes and dates:\nRoutes: {}\nDates: {}".format(routes, dates))
    completed_count = 0
    for date in dates:
        data, error = scrap(date, routes, job_id)
        final_res.extend(data)
        final_ero.extend(error)
        completed_count += 1
        log.info('===== PERCENT COMPLETE: ' + str((completed_count * 100) / len(dates)))

    report_excel_columns = ['Date', 'Departs', 'Dep Time', 'Arrives', 'Arr Time', 'Stops', 'Flight']
    for fare_type in fare_type_list:
        report_excel_columns.append(fare_name_tmpl.format(fare_type))

    write_to_excel(report_name, final_res, final_ero,
                   report_excel_columns, ['route', 'date', 'exe'])

    # write_to_excel(report_file_path_tmpl.format(job_id, error_rep_name), final_ero, )

    if send_email:
        log.debug('Sending Mail to "{}"'.format(email_to_send_report))
        send_mail(email_to_send_report, job_id, os.path.dirname(report_name))
        log.info('Mail sent to "{}"'.format(email_to_send_report))

    if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
        shutil.rmtree('chrome-profile')


if __name__ == '__main__':
    import logging

    logging.basicConfig(format='%(levelname)s --> %(message)s', level=logging.INFO)
    rootlog = logging.getLogger('werkzeug')
    rootlog.setLevel(logging.ERROR)

    rootlog = logging.getLogger('selenium')
    rootlog.setLevel(logging.ERROR)

    rootlog = logging.getLogger('urllib3')
    rootlog.setLevel(logging.ERROR)

    routes = ['SYD-CAN']  # , 'SYD-MEL'

    run(routes, 3, 4)

    print("Completed")
