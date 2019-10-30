import concurrent.futures
import urllib.request
import multiprocessing

URLS = ['http://www.foxnews.com/',
   'http://www.cnn.com/',
   'http://europe.wsj.com/',
   'http://www.bbc.co.uk/',
   'http://some-made-up-domain.com/','http://www.foxnews.com/',
   'http://www.cnn.com/',
   'http://europe.wsj.com/',
   'http://www.bbc.co.uk/',
   'http://some-made-up-domain.com/'
        ]

def load_url(url, timeout=30):
   with urllib.request.urlopen(url, timeout = timeout) as conn:
    return conn.read()

with concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:

   future_to_url = {executor.submit(load_url, url, 2): url for url in URLS}

   print("After thread")



   for future in concurrent.futures.as_completed(future_to_url):


       print(future)

       url = future_to_url[future]

       print(url)

       try:
          data = future.result()
       except Exception as exc:
          print('%r generated an exception: %s' % (url, exc))
       else:
          print('%r page is %d bytes' % (url, len(data)))

# import multiprocessing
#
# pool = multiprocessing.Pool(multiprocessing.cpu_count())
# result = pool.map(load_url, [url for url in URLS])
#
# print('All scheduled')