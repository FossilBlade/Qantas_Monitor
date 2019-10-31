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



############### DO NOT REMOVE BELOW ####################################
import chromedriver_binary  # Adds chromedriver binary to path

page_load_timeout = 45

START_URL = 'https://www.qantas.com/au/en/book-a-trip/flights.html'
user_agent_list = [
   #Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36',

    #Firefox
    # 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/70.0',
    # 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:61.0) Gecko/20100101 Firefox/70.0',
    # 'Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/70.0'
]

def write_to_excel(excel_path, data_list, column_list):

    if data_list==None or len(data_list)==0:
        print('Data List empty for creating Excel.')
        return


    print('Creating Excel')

    prevlen = len(data_list[0])
    for data in data_list:
        if prevlen != len(data):
            print("LENGTH NOT SAME")

        prevlen = len(data)

    df = pd.pandas.DataFrame.from_dict(data_list, dtype=str)
    writer = pd.ExcelWriter(excel_path, engine='xlsxwriter', options={'strings_to_urls': False})
    df.to_excel(writer, columns=column_list)
    writer.close()
    print('Excel Created at :' + os.path.abspath(excel_path))


def get_date_range(start_day, end_day):
    return [(datetime.date.today() + datetime.timedelta(days=x)).strftime('%d-%m-%Y') for x in
            range(start_day, end_day)]







class QantusScrapper:

    def __init__(self,date, routes_list,headless=True,close_driver=True):

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


    def __del__(self):
        if self.close_driver==True and self.driver:
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
        # self.driver.set_window_position(2000, 0)

        # # driver.maximize_window()
        # size = driver.get_window_size()
        # driver.set_window_size(size.get('width')/4, size.get('height'))
        # driver.set_window_position(2000, 0)

    def page_has_loaded(self):
        # self.log.info("Checking if {} page is loaded.".format(self.driver.current_url))
        page_state = self.driver.execute_script('return document.readyState;')
        return page_state == 'complete'

    def wait_for_ajax(self):
        wait = WebDriverWait(self.driver, 15)
        try:
            wait.until(lambda driver: driver.execute_script('return jQuery.active') == 0)
            wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
        except Exception as e:
            pass

    def __process_displayed_months(self,day,mon_name,year):
        tables = self.driver.find_elements_by_xpath(
            '//div[@class="date-picker__calendar-container"]//table[@class="date-picker__calendar-table"]')
        displayed_mon_nos = []
        for table in tables:
            input_mon_year = "{} {}".format(mon_name, year)
            display_st = table.text.strip()
            if input_mon_year in display_st:

                display_day = table.find_element_by_xpath(
                    './/span[@class="date-picker__calendar-weekdays-items-text" and text()="{}"]'.format(day))
                display_day.click()
                # driver.execute_script("arguments[0].click();", display_day)
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

        displayed_mon_nos = self.__process_displayed_months(day,mon_name,year)

        if len(displayed_mon_nos)==2:
            while len(displayed_mon_nos)!=0:
                self.driver.find_element_by_css_selector(
                    '.date-picker__arrow.date-picker__arrow-right.qfa1-arrow-icon').click()
                displayed_mon_nos = self.__process_displayed_months(day,mon_name, year)






    def __click_one_way(self):
        try:
            oneway = self.driver.find_element_by_xpath('//*[@id="oneway"]')
            self.driver.execute_script("arguments[0].click();", oneway)
        except:
            self.driver.save_screenshot("screenshot1.png")
            try:
                old_form_link = self.driver.find_element_by_xpath("//p[contains(text(),'still working through the accessibility functionality of this form')]//a")

                print(old_form_link.get_attribute('href'))

                self.driver.get(old_form_link.get_attribute('href'))

                oneway = self.driver.find_element_by_xpath('//*[@id="oneway"]')
                self.driver.execute_script("arguments[0].click();", oneway)
            except:
                print_exc()
                self.driver.save_screenshot("screenshot2.png")
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

        # place_input.send_keys(Keys.CONTROL + "a")
        # place_input.send_keys(Keys.DELETE)
        # place_input.send_keys(place_code)
        # sleep(.1)
        # place_opt = self.driver.find_element_by_xpath(
        #     '//*[@id="typeahead-list-item-from-list"]//strong[text()="{}"]'.format(place_code))
        # place_opt.click()

    def __click_search(self):
        sleep(1)
        self.driver.find_element_by_xpath('//button[text()="SEARCH FLIGHTS"]').click()

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, 'upsell-itinerary-avail')))

        body = self.driver.find_element_by_id('upsell-container-bound0')
        body_html = body.get_attribute("outerHTML")
        self.all_fare_body_htmls.append(body_html)

        extra_fare_classes_names =[]
        try:
            extra_fare_classes = self.driver.find_elements_by_xpath('//div[@class="cabin-selector-row"]//button')[1:]
            for fare_class in extra_fare_classes:
                extra_fare_classes_names.append(fare_class.text)

        except:
            pass

        for fare_class_name in extra_fare_classes_names:
            fare_class = self.driver.find_element_by_xpath('//div[@class="cabin-selector-row"]//button[contains(text(),"{}")]'.format(fare_class_name))
            # fare_class_text = fare_class.text
            fare_class.click()

            self.wait_for_ajax()



            try:
                self.driver.find_element_by_xpath("//h3[contains(text(),'No compatible flights')]")
                continue
            except:
                pass


            # btn = WebDriverWait(self.driver, 15).until(
            #     EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'fare-name') and contains(text(),'{}')]".format(fare_class_name))))
            #
            # WebDriverWait(self.driver, 10).until(
            #     EC.presence_of_all_elements_located((By.TAG_NAME, 'upsell-itinerary-avail')))


            # while self.page_has_loaded() == False:
            #     sleep(.5)



            body = self.driver.find_element_by_id('upsell-container-bound0')
            body_html = body.get_attribute("outerHTML")
            self.all_fare_body_htmls.append(body_html)


        print('Flight Summary Found')

    def __save_data(self):


        for fare_classes_html in self.all_fare_body_htmls:

            soup = BeautifulSoup(fare_classes_html, "html.parser")

            sumamry_rows = soup.findAll("upsell-itinerary-avail")

            for row in sumamry_rows:

                flight_detail = {'date': self.date, 'src': None, 'src_time': None, 'dst': None, 'dst_time': None,
                                 'red_e-deal': None,
                                 'flex': None, 'business': None, 'business_classic_reward': None,
                                 'economy_classic_reward': None, 'stops': 0, 'f_no': None,'sale':None,'saver':None,'premium_economy_sale':None,'premium_economy_flex':None,'first_saver':None,'first_flex':None,'business_saver':None,'business_flex':None}

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

                self.results.append(flight_detail)
                # print(
                #     'Flight Number: {} (Stops: {})\n\t {} : {}\n\t {} : {}'.format(flight_no, len(segments) - 1, src,
                #                                                                    src_time,
                #                                                                    dst, dst_time))
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
                    # print("\t\t{}: {}".format(name, amt))

        print('Data Extracted')



    def __search(self):
        print('Searching for Route [{}] for Date [{}] on page: {} '.format(self.route, self.date, START_URL))
        self.driver.get(START_URL)

        if self.first_search_done == False:
            print('Entering DATE, SRC and DST.')
            self.__click_one_way()

            self.__enter_place_code('src')
            self.__enter_place_code('dst')

            self.__click_on_date()
            self.first_search_done =True
        else:
            print('Entering SRC and DST Only')
            self.__enter_place_code('src')
            self.__enter_place_code('dst')

        self.__click_search()

        self.__save_data()


    def loop_over_routes(self):
        for self.route in self.routes_list:

            try:
                self.__search()
            except:
                print_exc()
                self.errors.append({'route': self.route, 'date': self.date, 'exe': sys.exc_info()[0]})





def scrap(date,routes):
    scrapper = QantusScrapper(date, routes, headless=False, close_driver=False)
    scrapper.loop_over_routes()
    return scrapper.results,scrapper.errors



def run(routes: list, start_day: int, end_day: int):


    if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
        shutil.rmtree('chrome-profile')

    dates = get_date_range(start_day, end_day)
    routes = list(set(routes))

    final_res = []
    final_ero = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        future_to_scrappers = {executor.submit(scrap, date, routes): "{}_{}".format(date,routes) for date in dates}

        # executor.submit(combine_and_create_xlsx,future_to_scrappers)

        # print("After thread")

        for future in concurrent.futures.as_completed(future_to_scrappers):

            print(future)

            date_route = future_to_scrappers[future]

            try:
                data, error = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (date_route, exc))
            else:
                final_res.extend(data)
                final_ero.extend(error)


                # print(error)
                #
                #
                print(json.dumps(data, indent=2))
                # print(json.dumps(error, indent=2))

    write_to_excel('db/Qantus_Data.xlsx', final_res,
                   ['f_no', 'date', 'stops', 'src', 'src_time', 'dst', 'dst_time', 'red_e-deal',
                    'flex', 'business', 'business_classic_reward',
                    'economy_classic_reward', 'sale', 'saver','premium_economy_sale','premium_economy_flex','first_saver','first_flex','business_saver','business_flex'])

    write_to_excel('db/Error.xlsx',final_ero,['route','date','exe'])

    if os.path.exists('chrome-profile') and os.path.isdir('chrome-profile'):
        shutil.rmtree('chrome-profile')




if __name__ == '__main__':
    import time


    routes = ['SYD-CAN'] # , 'SYD-MEL'



    start_time = time.time()
    run(routes, 120,121)
    end_time = time.time()
    print("Time to complete: {}".format(end_time - start_time))
