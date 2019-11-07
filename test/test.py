import datetime
import multiprocessing
# job_id = datetime.date.today().strftime('%Y%m%d%h%M%s')
job_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

print(multiprocessing.cpu_count())