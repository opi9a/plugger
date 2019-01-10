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

pads = [35, 10]

class TestPlug:
    # creates a simulated plug object
    def __init__(self):
        self.is_on = False
        self.info = { 'alias': 'Test Plug',
                      'model': 'Test Plug',
                    }

    def turn_on(self):
        self.is_on = True

    def turn_off(self):
        self.is_on = False


def main(panel_ip='192.168.1.161/meters.xml', socket_ip='192.168.1.61',
         threshold=0.7, interval=30, single_shot=False, max_tries=None,
         log_file='log.csv', test_plug=False):
    """Do iterations over a loop which tests the power output at panel_ip,
    and manages the state of a plug at socket_ip, according to the threshold
    power output level.

    If pass single_shot=True, will do one test and exit, after making
    max_tries number of attempts to make a successful read and switch

    Otherwise will operate continuously. Interrupt with ctrl-c

    To test:
        pass socket_ip=None and test_plug=True to simulate the plug
        pass a test xml page on localserver as panel_ip, eg:
            <line1>x</line1>
            <OutputPower>99</OutputPower>
            <line3>x</line3>
        .. and serve the page the project folder with:
            $ python -m http.server
        (can edit and save this file on the fly to simulate panel output)

    """

    # create a plug instance
    if socket_ip is not None:
        try:
            plug = SmartPlug(socket_ip)

        except:
            print('Could not find a plug at', socket_ip)
            return 1

    elif test_plug:
        plug = TestPlug()

    else:
        print('need either a socket_ip or pass test_plug=True')
        return 1


    interval_by_min = f'{str(interval // 60)} min, {str(interval % 60)} sec'

    splash_width = 60
    info = plug.info
    print('')
    print('*'*12, 'PLUGGER ENERGY MANAGEMENT SYSTEM', '*'*12)
    print('')
    print('version'.ljust(pads[0]), '0.1')
    print('')
    print('Plug IP address:'.ljust(pads[0]), socket_ip)
    print('Plug name'.ljust(pads[0]), info['alias'])
    print('Plug model'.ljust(pads[0]), info['model'])
    print('Initial plug state:'.ljust(pads[0]), "ON" if plug.is_on else "OFF")
    print('')
    print('Panel IP address:'.ljust(pads[0]), panel_ip)
    print('Panel power output threshold:'.ljust(pads[0]), threshold)
    print('')
    print('Test interval:'.ljust(pads[0]), interval_by_min)
    print('Testing mode:'.ljust(pads[0]),
          'single shot' if single_shot else 'continuous')
    print('Max attempts (if single shot):'.ljust(pads[0]),
          max_tries if single_shot else 'n/a')
    print('')
    print('*'*59)
    print('')


    # initialise the log file if reqd
    if not os.path.exists(log_file):
        with open(log_file, 'a') as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(CSV_COLUMNS)


    tries = 0

    # main loop
    while True:

        ts = time.strftime('%d/%m/%y %H:%M:%S')
        log_list = [ts]

        if single_shot:
            print(ts, f'[{tries + 1}/{max_tries}]'.ljust(7), end=" ")
        else:
            print(ts, end=" ")


        # try to read the panel's current output
        success, panel_output = get_panel_output(panel_ip=panel_ip,
                                                 target='OutputPower')

        if not success:
            print(f'failed to get panel output, error: {panel_output}')
            if single_shot:
                tries += 1
                if tries == max_tries:
                    return 0
            time.sleep(interval)
            continue

        log_list.extend([success, panel_output])
        print('panel reading: ' + str(panel_output).ljust(pads[1]), end= ' ')

        try:
            socket_state = plug.is_on
        except:
            print('cannot find plug')
            if single_shot:
                tries += 1
                if tries == max_tries:
                    return 0
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
                    if single_shot:
                        tries += 1
                        if tries == max_tries:
                            return 0
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
                    if single_shot:
                        tries += 1
                        if tries == max_tries:
                            return 0
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
            socket_state = 'not found after changes'
            continue

        log_list.append(socket_state)

        # write out log 
        with open(log_file, 'a') as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(log_list)

        if single_shot:
            return 0

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
        return False, "no response from " + url

    if not response.ok:
        return False, str(response)

    xml_text = response.text

    result = None

    try:
        result = float(xml_text.split(target)[1][1:-2])
    except:
        return False, f'cannot find {target} in xml'

    return True, float(result) 


if __name__ == "__main__":

    print(sys.argv)
    if not 'help' in sys.argv:
        print('\nType "python plugger.py help" for inputs prompt')

    if 'test' in sys.argv:
        main(panel_ip=sys.argv[1],
             socket_ip=None,
             test_plug=True,
             threshold=float(sys.argv[3]),
             interval=int(sys.argv[4]),
             max_tries=int(sys.argv[5]),
             single_shot= bool(int(sys.argv[5])))

    elif len(sys.argv) == 1:
        main()

    elif (len(sys.argv) == 2) & (sys.argv[1] == 'single'):
        main(single_shot=True, max_tries=100)

    elif len(sys.argv) == 6:
        main(panel_ip=sys.argv[1],
             socket_ip=sys.argv[2],
             threshold=float(sys.argv[3]),
             interval=int(sys.argv[4]),
             max_tries=int(sys.argv[5]),
             single_shot= bool(int(sys.argv[5])))

    else:
        pad = 15
        print('\nFor simple use with default parameters, just type'
              ' "python plugger.py"')
        print('\nPlease provide:\n',
              'panel_ip'.ljust(pad) + 'eg 192.168.1.161/meters.xml\n',
              'socket_ip'.ljust(pad) + 'eg 192.168.1.61\n',
              'threshold'.ljust(pad) + 'eg 0.7\n',
              'interval'.ljust(pad) + 'in seconds, so eg 300 for 5 mins\n',
              'max_tries'.ljust(pad) + 'if a single shot.'
              ' Use 0 for continuous operation\n')
        print('(all separated by spaces)\n')
        print('eg:\n python plugger.py 192.168.1.161/meters.xml',
              '192.168.1.61 0.7 0\n\n')
