
import sys
import subprocess
import argparse

class MCTPWrapper():
    def __init__(self):
        self.mc_id = None
        self.hrd_rv = None
        self.iid = None
        self.command = None
        self.channel_id = None
        self.pay_len = None
        self.payload_padding_len = 4
        self.checksum = '0 0 0 0'

        # TODO: enum in python?
        self.msg_type = {'MCTP': 0, 'PLDM':1, 'NCSI':2, 'ETH':3, 'NVME':4, 'SPDM':5, 'SecMsg':6}

        # @note this relies on other parameters being default as 0s.
        self.ncsi_commands = {
            'clear initial state':           {'iid':1,    'command':0},
            'select package':                {'iid':2,    'command':1},
            'deselect package':              {'iid':3,    'command':2},
            'enable channel':                {'iid':4,    'command':3},
            'disable channel':               {'iid':5,    'command':4},
            'reset channel':                 {'iid':6,    'command':5},
            'enable channel network tx':     {'iid':7,    'command':6},
            'disable channel network rx':    {'iid':8,    'command':7},
            'set link':                      {'iid':9,    'command':9,                       'pay_len':8},
            'get link status':               {'iid':0xa,  'command':0xa},
            'set vlan filter':               {'iid':0xb,  'command':0xb,                     'pay_len':8},
            'enable vlan':                   {'iid':0xc,  'command':0xc,                     'pay_len':4},
            'disable vlan':                  {'iid':0xd,  'command':0xd},
            'set mac address':               {'iid':0xe,  'command':0xe,                     'pay_len': 8, 'payload': "0x66 0x55 0x44 0x33 0x22 0x11 1 0"},
            'enable broadcast filtering':    {'iid':0xf,  'command':0x10,                    'pay_len': 4},
            'disable broadcast filtering':   {'iid':0x10, 'command':0x11},
            'get version id':                {'iid':0x11, 'command':0x15, 'channel_id':0x01},
            'dell oem set address':          {'iid':0x13, 'command':0x50,                    'pay_len':0x10, 'payload':"0x00 0x00 0x02 0xa2 0x02 0x07 0 1 6 11 22 33 44 55 66 0"},
            'dell oem get address':          {'iid':0x14, 'command':0x50,                    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x08 0 0'},
            'dell oem get passthrough':      {'iid':0x15, 'command':0x50,                    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x0c 0 0'},
            'dell oem enable wol':           {'iid':0x16, 'command':0x50,                    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x15 0 0'},
            'dell oem disable wol':          {'iid':0x17, 'command':0x50,                    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x16 0 0'},
            'dell oem get lldp':             {'iid':0x18, 'command':0x50,                    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x28 0 0'},
            'dell oem send ethernet frame':  {'iid':0x19, 'command':0x50,                    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x2b 0 0'},
            'dell oem get inventory':        {'iid':0x1a, 'command':0x50,                    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x00 0 0'},
            'dell oem get ext capability':   {'iid':0x1b, 'command':0x50, 'channel_id':2,    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x01 0 0'},
            'dell oem get part info':        {'iid':0x1c, 'comamnd':0x50, 'channel_id':3,    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x02 0 0'},
            'dell oem get temperature':      {'iid':0x1d, 'command':0x50, 'channel_id':0x1f, 'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x13 0 0'},
            'dell oem get payload versions': {'iid':0x1e, 'command':0x50, 'channel_id':0x1f, 'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x1a 0 0'},
            'dell oem get os driver version':{'iid':0x1f, 'command':0x50, 'channel_id':0x01, 'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x1c 0 0'},
            'dell oem get interface info':   {'iid':0x20, 'command':0x50, 'channel_id':0x02, 'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x29 0 0'},
            'dell oem get interface sensor': {'iid':0x21, 'command':0x50, 'channel_id':0x03, 'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x2a 0 0'},
            'get capabilitie':               {'iid':0x22, 'command':0x16},
            'get parameters':                {'iid':0x23, 'command':0x17},
            'dell oem get interface sensor wo sfp': {'iid':0x21, 'command':0x50, 'channel_id':0x03, 'pay_len':8, 'payload':' 0x00 0x00 0x02 0xa2 0x02 0x2a 0 0'}
            # TODO: this seems to be the same as a previous example

        }

        self.fixed_val_keys = ['SRC_ID', 'TAG', 'MSG_TYPE', 'MC_ID', 'HeaderRev', 'Rsv', 'IID',
                               'PacketType', 'Channel']

        self.response = dict()
        self.raw_response = None
        self.raw_response_list = None

        self.ncsi_res_parser = {'dell oem get temperature': {'payloadversion':4 ,
                                                             'command id':5,
                                                             'maximum temperature' :6,
                                                             'current temperature':7},

                                'get version id': {'alpha 2': 7,
                                                   'firmware name': "8 19",
                                                   'firmware version': (20, 23),
                                                   'pci did': (24, 25),
                                                   'pci vid': (25, 26),
                                                   'pci ssid': (27, 28),
                                                   'manufacturer id': (29, 32)}, # TODO string parsing in this example
                                'dell oem get invertory': {'firmware family version': (8, 11),
                                                           'type length type': 16,
                                                           'type length length': 17,
                                                           'device name': "18 53"},
                                'dell oem get ext capability': {'capability': (6, 9),
                                                                'dcb capability': 11,
                                                                'nic partitioning capability': 12,
                                                                'e-swtich capability': 13,
                                                                '# of pci physical functions': 14,
                                                                '# of pci virtual functions': 15},
                                'dell oem get part info': {'# of pci physical functions enabled': 6,
                                                           'partition id': 7,
                                                           'partition status': (8, 9),
                                                           'interface name': 10,
                                                           'length': 11,
                                                           'interface name': "12 46"},
                                'dell oem get payload versions': {'supported versions': 7},
                                'dell oem get os driver version': {'partition id': 6,
                                                                   'number of active drivers in TLVs':7,
                                                                   'interface name type':8,
                                                                   'length':9,
                                                                   'value':(10, 13)},
                                'dell oem get interface info': {'interface type': 7,
                                                                'data field byte 0': 8,
                                                                'data field byte 1': 9,
                                                                'data field byte 2': 10,
                                                                'data field byte 3': 11},
                                'dell oem get interface sensor': {'status':6,
                                                                  'identifier':7,
                                                                  'temp high alarm threshold': (8,9),
                                                                  'temp high warning threshold': (10, 11),
                                                                  'temperature value': (12, 13),
                                                                  'vcc voltage value': (14, 15),
                                                                  'tx bias current value': (16, 17),
                                                                  'tx output power value': (18, 19),
                                                                  'rx input power value': (20, 21),
                                                                  'flag bytes': (22, 25)}
                                }


        """
        self.response_parse_list = ["MCTP transport header",
                                    "MCTP header",
                                    "NCSI control message",
                                    "NCSI header",
                                    "Reason",
                                    "Payload"]
        """

    def pretty(self, d, indent=4):
        for key, value in d.items():
            if isinstance(value, dict):
                print('  ' * indent + str(key))
                self.pretty(value, indent+1)
            else:
                print('  ' * (indent+1) + f"{key}: {value}")

    # TODO check
    def dec_to_2_hex_str(self, dec):
        if dec > 2**13:
            raise ValueError("Payload length has 13 bits.")

        # ([12:8] and [7:0])
        return ("0", str(hex(dec))) if dec < 255 else (str(hex(dec-255)), str(hex(255)))

    def runall(self, args):
        args.pop('test')
        for cmd in self.ncsi_commands:
            args['ncsi_cmdstring'] = cmd
            self.run(**args)


    def run(self, verbose=True, bus=3, dst_eid=0, msg_type='NCSI', cml_decode_response=True,
            slave_addr=55, mc_id=0, hrd_rv=1, iid=1, command=0, channel_id=0, pay_len=0,
            payload=None, ncsi_cmdstring=None):

        self.mc_id = mc_id
        self.hrd_rv = hrd_rv
        self.iid = iid
        self.command = command
        self.channel_id = channel_id
        self.pay_len = pay_len
        self.payload = payload

        # override variables if cmd_string is defined
        if ncsi_cmdstring in self.ncsi_commands:
            for k in self.ncsi_commands[ncsi_cmdstring]:
                setattr(self, k, self.ncsi_commands[ncsi_cmdstring][k])

        parsed_pay_len = self.dec_to_2_hex_str(self.pay_len)

        cmd = ["mctp-util"]

        # decode response
        if cml_decode_response:
            cmd.append("-d")

        # slave address
        if slave_addr:
            cmd.extend(["-s", str(slave_addr)])

        # <bus> <dst_eid> <type>
        cmd.extend([str(bus), str(dst_eid), str(self.msg_type[msg_type])])

        # start of packet header
        packet_header = list()

        # MC_ID, HDR_RV, RESV, IID ...
        packet_header.append(str(self.mc_id))            # MC_ID,
        packet_header.append(str(self.hrd_rv)),          # HDR_RV
        packet_header.append("0")                        # RSVD
        packet_header.append(str(self.iid))              # IID
        packet_header.append(str(self.command))          # CMD
        packet_header.append(str(self.channel_id))       # CHANNEL_ID
        packet_header.extend(list(parsed_pay_len))       # PAYLOAD_LEN[12:8], PAYLOAD_LEN[7:0]
        packet_header.extend(["0"] * 8)                  # RSVD[63:0]

        # add NCSI packet header
        cmd.extend(packet_header)

        # payload
        #print(self.pay_len, self.payload)
        if self.payload:
            cmd.extend(self.payload.split(' '))

        # payload padding
        cmd.extend(['0']*self.payload_padding_len)

        # checksum
        cmd.extend(self.checksum.split(' '))

        if verbose:
            if ncsi_cmdstring in self.ncsi_commands:
                print("Running: ", ncsi_cmdstring)
            print("Running: " + " ".join(cmd))

        try:
            #res = subprocess.run(["python", "-c", "\"print(123)\""], capture_output=True, text=True)
            #res = subprocess.run(["dir"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            res = subprocess.run(cmd, capture_output=True, text=True)
            #print(res.stderr)
            #print("-------------")

            # get raw reponse line
            response_lines = res.stdout.splitlines()
            for i, l in enumerate(response_lines):
                if "raw response" in l:
                    self.raw_response = response_lines[i+1]
                    break
            if not self.raw_response:
                sys.exit("Command failed to have a raw reponse in stdout")

            self.raw_response_list = self.raw_response.split(' ')

            # assign MC_ID, HDR_RV, .... PAYLOAD_LEN, single byte vals
            for i, val in enumerate(self.raw_response_list):
                if i < len(self.fixed_val_keys):
                    self.response[self.fixed_val_keys[i]] = val
                else:
                    break

            self.response['PayLen'] = self.raw_response_list[i:i+10]
            self.response['ResponseCode'] = self.raw_response_list[i+10:i+12]
            self.response['ResponseReason'] = self.raw_response_list[i+12:i+14]
            self.response['Payload'] = self.raw_response_list[i+14:]

            if ncsi_cmdstring in self.ncsi_res_parser:
                self.response['NCSI Payload Parser'] = dict()
                for k, v in self.ncsi_res_parser[ncsi_cmdstring].items():
                    parse_string = False
                    if type(v) is str:
                        parse_string = True
                        v = [int(x) for x in v.split(" ")]
                    s = v if type(v) is int else v[0]
                    e = v+1 if type(v) is int else v[1] + 1
                    #print("k/v:", k, v, "s:e", s, e, "list", self.response['Payload'][s:e])
                    if parse_string:
                        self.response['NCSI Payload Parser'][k] = bytearray.fromhex("".join(self.response['Payload'][s:e])).decode()
                    else:
                        self.response['NCSI Payload Parser'][k] = self.response['Payload'][s:e]

            if verbose:
                print("Response:")
                self.pretty(self.response)

        except subprocess.CalledProcessError as e:
            print(e.output)

    def verify(self):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # @note default vals should be the same as default vals in run() so that
    #       both command line and python api behave the same
    parser.add_argument('-v', '--verbose', help='Verbose', type=bool, default=False, required=False)
    parser.add_argument('-t', '--test', help='Test all NCSI commands', type=bool, default=False, required=False)
    parser.add_argument('--bus', help='', type=int, default=3, required=False)
    parser.add_argument('--dst_eid', help='', type=int, default=0, required=False)
    parser.add_argument('--msg_type', help='', type=str, default='NCSI', required=False)
    parser.add_argument('--cml_decode_response', help='', type=bool, default=True, required=False)
    parser.add_argument('--slave_addr', help='Slave address', type=int, default=55, required=False)
    parser.add_argument('--mc_id', help='MC ID', type=int, default=0, required=False)
    parser.add_argument('--hrd_rv', help='Header revision', type=int, default=1, required=False)
    parser.add_argument('--iid', help='IID', type=int, default=1, required=False)
    parser.add_argument('--command', help='', type=int, default=0, required=False)
    parser.add_argument('--channel_id', help='', type=int, default=0, required=False)
    parser.add_argument('--pay_len', help='', type=int, default=0, required=False)
    parser.add_argument('--payload', help='', type=str, default=None, required=False)
    parser.add_argument('--ncsi_cmdstring', help='A NCSI command string that fills values automatically',
                        type=str, required=False)
    args = vars(parser.parse_args())
    m = MCTPWrapper()
    if args['test']:
        m.runall(args)
    else:
        args.pop('test')
        m.run(**args)
