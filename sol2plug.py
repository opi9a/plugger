import time
import os
import csv
# import requests
from requests_html import HTMLSession
# from bs4 import BeautifulSoup

from tplink_smartplug import SmartPlug

CSV_COLUMNS = ['datetime', 
               'panel_success',
               'panel_output',
               'socket_state',
               'action',
               'socket_state1',
              ]

pads = [30, 10]


def main(panel_ip, socket_ip, threshold,
         interval=300, log_file='log.csv'):

    # create a plug instance
    try:
        plug = SmartPlug(socket_ip)
    except:
        print('Could not find a socket at', socket_ip)
        return 1

    info = plug.info
    print('Found plug')
    print('- name'.ljust(pads[0]), info['alias'])
    print('- model'.ljust(pads[0]), info['model'])
    print('Initial state:'.ljust(pads[0]), "ON" if plug.is_on else "OFF")
    print('Threshold:'.ljust(pads[0]), threshold)
    print('')

    # initialise the log file if reqd
    if not os.path.exists(log_file):
        with open(log_file, 'a') as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(CSV_COLUMNS)


    # main loop
    while True:

        ts = time.strftime('%d/%m/%y %H:%M:%S')
        log_list = [ts]
        print(ts, end=' ')

        # try to read the panel's current output
        success, panel_output = get_panel_output(panel_ip)

        if not success:
            print(f'failed to get panel output, error: {panel_output}')
            continue

        log_list.extend([success, panel_output])
        print('panel reading: ' + str(panel_output).ljust(pads[1]), end= ' ')

        socket_state = plug.is_on
        log_list.append(socket_state)

        if panel_output >= threshold:
            if socket_state:
                log_list.append('leave on')
                print('leave on')
            
            else:
                plug.turn_on()
                print('** TURN ON **')
                log_list.append('activate')

        elif panel_output < threshold:
            if socket_state:
                plug.turn_off()
                print('** TURN OFF **')
                log_list.append('deactivate')
            
            else:
                log_list.append('leave off')
                print('leave off')

        # get a plug reading after any changes
        log_list.append(plug.is_on)

        # write out log 
        with open(log_file, 'a') as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(log_list)

        time.sleep(interval)



def get_panel_output(panel_ip=None, target='target'):
    """Returns tuple of success flag and value.
    If success, value is the power output of the panel.
    Otherwise it is the http response.
    """

    # get the panel web page
    url = 'http://' + panel_ip
    print('trying url:', url)
    session = HTMLSession()
    r = session.get(url)

    if not r.ok:
        return False, str(r)

    # render the web page - executing the js
    r.html.render()

    # get the target
    out = r.html.find(id=target)[0].text

    return True, float(out) 


# def get_panel_output(panel_ip=None, target='target'):
#     """Returns tuple of success flag and value.
#     If success, value is the power output of the panel.
#     Otherwise it is the http response.
#     """

#     url = 'http://' + panel_ip
#     print('trying url:', url)
#     response = requests.get(url)

#     if not response.ok:
#         return False, str(response)

#     soup = BeautifulSoup(response.text, 'html.parser')

#     out = soup.find(id=target).text

#     return True, float(out) 

