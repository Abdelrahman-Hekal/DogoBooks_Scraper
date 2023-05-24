from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
import pandas as pd
import time
import csv
import sys
import numpy as np

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_page_load_timeout(60)
    driver.maximize_window()

    return driver

def scrape_DoGoBooks(path):

    start = time.time()
    print('-'*75)
    print('Scraping DoGoBooks.com ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'DoGoBooks_data.xlsx'
        # getting the books under each category
        links = []
        nbooks, npages = 0, 0
        while True:
            npages += 1
            url = 'https://www.dogobooks.com/page/'
            url += str(npages)
            driver.get(url)
            try:
                # scraping books urls
                div = wait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//div[@id='latest_book_reviews']")))
                titles = wait(div, 5).until(EC.presence_of_all_elements_located((By.TAG_NAME, "h2")))
                for title in titles:
                    nbooks += 1
                    print(f'Scraping the url for book {nbooks}')
                    link = wait(title, 5).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                    links.append(link)

                # moving to the next page
                try:
                    # check if the last page reached
                    div = wait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//div[@id='paginator']")))
                    button = wait(div, 5).until(EC.presence_of_element_located((By.TAG_NAME, "a")))                 
                except:
                    break
            except Exception as err:
                print('The below error occurred during the scraping from DoGoBooks.com, retrying ..')
                print('-'*50)
                print(err)
                print('-'*50)
                driver.quit()
                time.sleep(10)
                driver = initialize_bot()

        # saving the links to a csv file
        print('-'*75)
        print('Exporting links to a csv file ....')
        with open('DoGoBooks_links.csv', 'w', newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Link'])
            for row in links:
                writer.writerow([row])

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        name = path.split('\\')[-1][:-4]
        name = name + '_data.xlsx'
    else:
        df_links = pd.read_csv('DoGoBooks_links.csv')

    links = df_links['Link'].values.tolist()

    try:
        data = pd.read_excel(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass

    # scraping books details
    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        try:
            if link in scraped: continue
            driver.get(link)           
            details = {}
            print(f'Scraping the info for book {i+1}\{n}')

            # title and title link
            title_link, title = '', ''
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).get_attribute('textContent').title() 
            except:
                print(f'Warning: failed to scrape the title for book: {link}')            
                
            details['Title'] = title
            details['Title Link'] = title_link            
            
            # Author
            author = ''
            try:
                author = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.author.stacked"))).get_attribute('textContent').replace('By', '').strip()
            except:
                print(f'Warning: failed to scrape the author for book: {link}')            
                
            details['Author'] = author


            info = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.details")))

            # book info
            cols = ['Cover', 'Publisher', 'Publication date', 'Number of pages', 'ISBN-10', 'ISBN-13']
                
            for col in cols:
                details[col] = ''

            divs = wait(info, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.details-row")))
            for div in divs:
                try:
                    text = div.get_attribute('textContent')
                    if 'ISBN-10' in text:
                        details['ISBN-10'] = text.split(' ')[-1].strip()
                    elif 'ISBN-13' in text:
                        details['ISBN-13'] = text.split(' ')[-1].strip()
                    elif 'Published' in text:
                        if 'by ' in text:
                            details['Publisher'] = text.split('by ')[-1].strip()
                            if 'on ' in text.split('by ')[0].strip():
                                details['Publication date'] = text.split('by ')[0].split('on ')[-1].strip()
                        elif 'on ' in text:
                            details['Publication date'] = text.split('on ')[-1].strip()
                    elif 'pages' in text:
                        if ', ' in text:
                            details['Cover'] = text.split(',')[0].strip()
                            details['Number of pages'] = text.split(',')[1].replace('pages', '').strip()
                        else:
                            details['Number of pages'] = text.replace('pages', '').strip()
                    elif 'Paperback' in text or 'Hardcover' in text or 'Kindle' in text:
                        details['Cover'] = text
                except:
                    pass            

            # Amazon link
            details['Amazon link'] = ''          
            try:
                buttons = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.btn.btn-success")))
                for butt in buttons:
                    if "Continue" in butt.get_attribute('textContent') and'www.amazon.com' in butt.get_attribute('href'):
                        details['Amazon link'] = butt.get_attribute('href')  
                        break
            except:
                pass           
                
            # rating
            rating = ''
            try:
                rating = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.rating.value-title"))).get_attribute('textContent')
                rating = float(rating)
                if rating > 5.0 or rating == 0.0:
                    rating = ''
            except:
                pass                       
            details['Rating'] = rating               
            
            # num of ratings
            nratings = ''
            try:
                nratings = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.rating-count.votes"))).get_attribute('textContent')
            except:
                pass                       
            details['Number Of Ratings'] = nratings             
            # num of reviews
            nrevs = ''
            try:
                nrevs = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.review-count.count"))).get_attribute('textContent')
            except:
                pass                       
            details['Number Of Reviews'] = nrevs             
            
            # num of followers
            nfollows = ''
            try:
                nfollows = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//span[@class='num-followers label label-warning label-as-badge']"))).get_attribute('textContent').split(' ')[0]
            except:
                pass                       
            details['Number Of Followers'] = nfollows             
            
            # other info
            int_lvl, read_lvl, ATOS, count = '', '', '', ''
            try:
                table = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//table[@class='table reading-levels']")))
                tds = wait(table, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "td")))
                for j, td in enumerate(tds):
                    if j == 0:
                        int_lvl = td.get_attribute('textContent').replace('n/a', '')
                    elif j == 1:
                        read_lvl = td.get_attribute('textContent').replace('n/a', '')    
                    elif j == 3:
                        ATOS = td.get_attribute('textContent').replace('n/a', '')
                    elif j == 4:
                        count = td.get_attribute('textContent').replace('n/a', '')
            except:
                pass                       
            details['Interest Level'] = int_lvl 
            details['Reading Level'] = read_lvl 
            details['ATOS'] = ATOS
            details['Word Count'] = count                          

            # appending the output to the datafame        
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except:
            pass

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'DoGoBooks.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_DoGoBooks(path)

