import time
import os
import sys
import csv
import requests

from tplink_smartplug import SmartPlug

CSV_COLUMNS = ['datetime', 
               'panel_success',
               'panel_output',
               'socket_state',
               'action',
               'socket_state1',
              ]

pads = [30, 10]

class TestPlug:
    def __init__(self):
        self.is_on = False
        self.info = { 'alias': 'testing',
                      'model': 'testing',
                    }

    def turn_on(self):
        self.is_on = True

    def turn_off(self):
        self.is_on = False


def main(panel_ip, socket_ip=None, threshold=0,
         interval=300, log_file='log.csv',
         test_plug=False):
    """Run an infinite loop which tests the power output at panel_ip,
    and manages the state of a plug at socket_ip, according to the threshold
    power output level.

    Interrupt with ctrl-c

    To test:
        pass socket_ip=None and test_plug = True to simulate the plug
        pass a test xml page on localserver as panel_ip, eg:
            <line1>x</line1>
            <OutputPower>99</OutputPower>
            <line3>x</line3>
        .. and serve the page with:
            $ python -m http.server
        .. issued in the project folder

    """

    # create a plug instance
    if socket_ip is not None:
        try:
            plug = SmartPlug(socket_ip)
            print('Found plug')

        except:
            print('Could not find a socket at', socket_ip)
            return 1

    elif test_plug:
        print('using test plug')
        plug = TestPlug()

    else:
        print('need either a socket_ip or pass test_plug=True')
        return 1

    info = plug.info
    print('- name'.ljust(pads[0]), info['alias'])
    print('- model'.ljust(pads[0]), info['model'])
    print('Initial state:'.ljust(pads[0]), "ON" if plug.is_on else "OFF")
    print('Threshold set:'.ljust(pads[0]), threshold)
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
        success, panel_output = get_panel_output(panel_ip=panel_ip,
                                                 target='OutputPower')

        if not success:
            print(f'failed to get panel output, error: {panel_output}')
            continue

        log_list.extend([success, panel_output])
        print('panel reading: ' + str(panel_output).ljust(pads[1]), end= ' ')

        try:
            socket_state = plug.is_on
        except:
            print('cannot find plug')
            time.sleep(interval)
            continue

        log_list.append(socket_state)

        if panel_output >= threshold:
            if socket_state:
                log_list.append('leave on')
                print('leave on')
            
            else:
                try:
                    plug.turn_on()
                except:
                    print('cannot find plug')
                    time.sleep(interval)
                    continue
                print('** TURN ON **')
                log_list.append('activate')

        elif panel_output < threshold:
            if socket_state:
                try:
                    plug.turn_off()
                except:
                    print('cannot find plug')
                    time.sleep(interval)
                    continue
                print('** TURN OFF **')
                log_list.append('deactivate')
            
            else:
                log_list.append('leave off')
                print('leave off')

        # log a plug reading after any changes
        try:
            socket_state = plug.is_on
        except:
            print('cannot find plug')
            time.sleep(interval)
            continue

        log_list.append(socket_state)

        # write out log 
        with open(log_file, 'a') as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(log_list)

        time.sleep(interval)
  

def get_panel_output(panel_ip=None, target=None):
    """Returns tuple of success flag and value.
    If success, value is the power output of the panel.
    Otherwise it is the http response.

    xml_text parameter is for testing (without getting url)
    """

    url = 'http://' + panel_ip

    try:
        response = requests.get(url)
    except:
        return False, "no get response from " + url

    if not response.ok:
        return False, str(response)

    xml_text = response.text

    result = None

    if target in xml_text:
        result = xml_text.split(target)[1][1:-2]
    else:
        print(f"cannot find {target} in xml")
        return False, f'cannot find {target} in xml'

    return True, float(result) 

if __name__ == "__main__":
    print('called')
    print(sys.argv)

    if 'test' in sys.argv:
        main('0.0.0.0:8000/test.xml', None,
             threshold=50, interval=3, test_plug=True)

    elif len(sys.argv) == 4:
        main(sys.argv[1], sys.argv[2], sys.argv[3]) 

    else:
        print('I am unsure what you are trying to do')
