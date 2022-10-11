#!/usr/bin/python3
import sys
import subprocess
import argparse

class SMBusWrapper():
    def __init__(self):
        self.res = None

        self.sensor_reading_reg_map = {
            'chip thermal margin': 0x00,
            'chip junction temperature': 0x01,
            'chip termperature offset': 0x11,
            'power consumption': 0x88
        }

        self.counter_type_map = {
            'rx receive count': 0x00,
            'rx error count': 0x01,
            'rx drop count': 0x02,
            'tx send count': 0x03,
            'tx error count': 0x04,
            'tx drop count': 0x05,
        }

        self.op_code_parse_map = {
            0x00: "success",
            0x01: "pending",
            0x80: "invalid request",
            0x81: "not ready",
            0x82: "busy",
            0x83: "not exist"
        }

    def cmd_string_parse_map(self):
        return {
            'sensor reading': {},
            'get mac counter': {'op_code': 0, 'counters': (1, 6), 'pec': 7},
            'clear mac counter': {'op_code': 0, 'pec': 1},
            'get ras record': {'op_code': 0, 'time': (1, 4), 'message length': 5, 'message': (6, self.n_bytes), 'pec': 7},
            'get ras record count': {'op_code': 0, 'record numbers': 1},
            'get byte data': {'index': 0, 'byte_data': 1},
            'get string data': {'index': 0, 'bytes': (1, self.n_bytes), 'pec':self.n_bytes+1},
            'send async request': {'op_code': 0, 'sequence': 1, 'exp_time': (2, 3)},
            'query async request': {'op_code': 0, 'sequence': 1, 'bytes': (3, 3+self.n_bytes), 'pec': 3+self.n_bytes+1},
            'get asping reset': {'op_code': 0, 'send_probes': 1, 'send broadcast': 2, 'received response':3,
                                 'target ip': (4, 7), 'source ip': (8, 11), 'device name': (12, 27), 'mac addr': (28, 33), 'time': (34, 37)}
        }

    # @note this could be slow, could make dict elements as static strings and
    # use eval() to return corresponding dynamic lists
    def cmd_string_map(self):
        return {
            'sensor reading': [self.slave_addr, str(hex(self.sensor_reading_reg_map[self.thermal_reg_string])), 'i', '1'],
            'get mac counter': ["w5@"+self.slave_addr, "0x40", str(hex(self.counter_type_map[self.counter_type_string])), self.cgx, self.lmac, self.pec, "r8"],
            'clear mac counter': ["w5@"+self.slave_addr, "0x41", str(hex(self.counter_type_map[self.counter_type_string])), self.cgx, self.lmac, self.pec, "r2"],
            'get ras record': ["w1@"+self.slave_addr, "0x60", "r160"],
            'get ras record count': ["w1@"+self.slave_addr, "0x61", "r2"],
            'get byte data': ["w2@"+self.slave_addr, "0x80", self.index, "r2"],
            'get string data': ["w2@"+self.slave_addr, "0x81", self.index, "r"+self.string_data_len],
            'send async request': ["w"+self.n_bytes+"@"+self.slave_addr, "0x82", self.index, self.sent_bytes, self.pec, "r6"],
            'query async request': ["w2@"+self.slave_addr, "0x83", self.index, "r"+self.n_bytes],
            'get asping reset': ["w2@"+self.slave_addr, "0x84", self.index, "r38"],
        }

    # @note already implemented above def cmd_string_map
    # all the prepare functions could be replaced by a single dict of lists that tells the sequence
    # to write for each cmd_string, but wN@slave_addr makes it not ideal and bothering to implement
    '''
    def prepare_sensor_reading_cmd(self):
        self.cmd.append(self.slave_addr)
        self.cmd.append(self.sensor_reading_reg_map[self.thermal_reg_string] if self.thermal_reg_string else self.reg)

        self.cmd.append("i")
        self.cmd.append("1")

    def prepare_get_mac_counter_cmd(self):
        self.cmd.append("w5@"+self.slave_addr)
        self.cmd.append(self.op_command)
        self.cmd.append(self.counter_type_string)
        self.cmd.append(self.cgx)
        self.cmd.append(self.lmac)
        self.cmd.append(self.pec)

        self.cmd.append("r8")

    def prepare_clear_mac_counter_cmd(self):
        self.cmd.append("w5@"+self.slave_addr)
        self.cmd.append(self.op_command)
        self.cmd.append(self.counter_type_string)
        self.cmd.append(self.cgx)
        self.cmd.append(self.lmac)
        self.cmd.append(self.pec)

        self.cmd.append("r2")

    def prepare_get_ras_record_cmd(self):
        self.cmd.append("w1@"+self.slave_addr)
        self.cmd.append(self.op_command)
        self.cmd.append("r160")

    def prepare_get_ras_record_count_cmd(self):
        self.cmd.append("w1@"+self.slave_addr)
        self.cmd.append(self.op_command)

        self.cmd.append("r2")

    def prepare_get_byte_data_cmd(self):
        self.cmd.append("w2@"+self.slave_addr)
        self.cmd.append(self.op_command)
        self.cmd.append(self.index)

        self.cmd.append("r2")

    def prepare_get_string_data_cmd(self):
        self.cmd.append("w2@"+self.slave_addr)
        self.cmd.append(self.op_command)
        self.cmd.append(self.index)

        self.cmd.append("r"+self.string_data_len)

    def prepare_send_async_request_cmd(self):
        self.cmd.append("w"+self.n_bytes+"@"+self.slave_addr)
        self.cmd.append(self.op_command)
        self.cmd.append(self.index)
        self.cmd.append(self.sent_bytes)
        self.cmd.append(self.pec)

        self.cmd.append("r6")

    def prepare_query_async_request_cmd(self):
        self.cmd.append("w2@"+self.slave_addr)
        self.cmd.append(self.op_command)
        self.cmd.append(self.index)

        self.cmd.append("r"+self.n_bytes)

    def prepare_get_asping_reset(self):
        self.cmd.append("w2@"+self.slave_addr)
        self.cmd.append(self.op_command)
        self.cmd.append(self.index)

        self.cmd.append("r38")
    '''
    def parse(self):
        if not self.cmd_string:
            sys.exit("cmd_string must be defined to parse")

        self.raw_response = self.res.stdout.splitlines()[0]
        self.raw_response_list = self.raw_response.split(' ')

        self.response = dict()
        for k, v in self.cmd_string_parse_map()[self.cmd_string].items():
            s = v if type(v) is int else v[0]
            e = v+1 if type(v) is int else v[1] + 1
            self.response[k] = self.raw_response_list[s:e]
            if k == 'op_code':
                self.response['op_code_descp'] = self.op_code_parse_map[int(self.response[k])]

    def pretty(self, d, indent=1):
        for key, value in d.items():
            if isinstance(value, dict):
                print('    ' * indent + str(key) + ':')
                self.pretty(value, indent+1)
            else:
                print('    ' * (indent) + f"{key}: {value}")

    def stringfy(self):
        self.bus = str(self.bus)
        self.slave_addr = str(self.slave_addr)
        self.reg = str(self.reg)
        self.cgx = str(self.cgx)
        self.lmac = str(self.lmac)
        self.pec = str(self.pec)
        self.index = str(hex(self.index))
        self.string_data_len = str(self.string_data_len)
        self.n_bytes = str(self.n_bytes)
        self.sent_bytes = str(self.sent_bytes)

    def run(self, verbose=True, i2c_command='i2cget', bus=3, cmd_string='sensor reading',
            slave_addr=0x55, thermal_reg_string='chip thermal margin', reg=0x00, op_command=0x00,
            counter_type_string='rx receive count', cgx=0, lmac=0, pec=0, index=0, string_data_len=0,
            n_bytes=0, sent_bytes=None):
        self.verbose = verbose
        self.i2c_command = i2c_command
        self.bus = bus
        self.cmd_string = cmd_string
        self.slave_addr = slave_addr
        self.reg = reg
        self.thermal_reg_string = thermal_reg_string
        self.op_command = op_command
        self.counter_type_string = counter_type_string
        self.cgx = cgx
        self.lmac = lmac
        self.pec = pec
        self.index = index
        self.string_data_len = string_data_len
        self.n_bytes = n_bytes
        self.sent_bytes = sent_bytes
        # case for "send async command"
        if self.sent_bytes and not self.n_bytes:
            self.n_bytes = len(self.sent_bytes)

        self.stringfy()

        if self.i2c_command:
            self.cmd = [self.i2c_command]
        else:
            if self.cmd_string == None:
                sys.exit('i2c_command must be defined, or define cmd_string')
            elif self.cmd_string == 'get sensor reading':
                self.cmd = ['i2cget']
            else:
                self.cmd = ['i2ctransfer']

        self.cmd.append('-y')

        self.cmd.append(self.bus)

        if self.cmd_string:
            print(self.cmd_string)
            self.cmd.extend(self.cmd_string_map()[self.cmd_string])
            if self.verbose:
                print(' '.join(self.cmd))

        try:
            #res = subprocess.run(["python", "-c", "\"print(123)\""], capture_output=True, text=True)
            #res = subprocess.run(["dir"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.res = subprocess.run(self.cmd, capture_output=True, text=True)
            #print(res.stderr)
            #print("-------------")
        except subprocess.CalledProcessError as e:
            print(e.output)

        self.parse()

        if self.verbose:
            self.pretty(self.response)



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
        self.msg_type_keys = {'MCTP': 0, 'PLDM':1, 'NCSI':2, 'ETH':3, 'NVME':4, 'SPDM':5, 'SecMsg':6}

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
            'dell oem get inventory':        {'iid':0x1a, 'command':0x50, 'channel_id':1,    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x00 0 0'},
            'dell oem get ext capability':   {'iid':0x1b, 'command':0x50, 'channel_id':2,    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x01 0 0'},
            'dell oem get part info':        {'iid':0x1c, 'command':0x50, 'channel_id':3,    'pay_len':8,    'payload':'0x00 0x00 0x02 0xa2 0x02 0x02 0 0'},
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

        self.mctp_commands = {
            'set eid to 0x0a': {'payload': "0x80 0x1 0x0 0xa"},
            'get eid': {'payload': "0x80 0x2"},
            'set uid': {'payload': "0x80 0x3"},
            'get version': {'payload': "0x80 0x4 0x0"},
            'get pldm version support': {'payload': "0x80 0x4 0x1"},
            'get message type support': {'payload': "0x80 0x5"}
        }

        """
         self.mctp_res_parser = {
            'set eid to 0x0a': {'Rq[7] D[6] IID[4:0]': 3,
                                'command code': 4,
                                'completion code': 5,
                                'data':
            }
        }
        """
        self.pldm_commands = {}

        self.ncsi_fixed_val_keys = ['SRC_ID', 'TAG', 'MSG_TYPE', 'MC_ID', 'HeaderRev', 'Rsv', 'IID',
                                    'PacketType', 'Channel']

        self.mctp_fixed_val_keys = ['src_eid', 'tag', 'msg_type', 'Rq[7] D[6] IID[4:0]', 'command code', 'completion code']

        self.response = dict()
        self.raw_response = None
        self.raw_response_list = None

        self.ncsi_res_parser = {
            'dell oem get temperature': {'payloadversion':4 ,
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
            'dell oem get inventory': {'firmware family version': (8, 11),
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

    def pretty(self, d, indent=1):
        for key, value in d.items():
            if isinstance(value, dict):
                print('    ' * indent + str(key) + ':')
                self.pretty(value, indent+1)
            else:
                print('    ' * (indent) + f"{key}: {value}")

    # TODO check
    def dec_to_2_hex_str(self, dec):
        if dec > 2**13:
            raise ValueError("Payload length has 13 bits.")

        # ([12:8] and [7:0])
        return ["0", str(hex(dec))] if dec < 255 else [str(hex(dec-255)), str(hex(255))]

    def runall(self, args):
        '''
        17, 25, 26, 27, 28, 29, 30, 31, 32, 35
        ./channel-util -n 0 0x01 0x95 0xf1 0xf1 0xf1 0x00 0x00 0x00 0x00 0x00 0x4f 0x43 0x54 0x45 0x4f 0x4e 0x20 0x42 0x45 0x54 0x41 0x00 0x01 0x01 0x00 0xa0 0xaa 0xaa 0xbb 0xbb 0xcc 0xcc 0xdd 0xdd 0x00 0x00 0x02 0xa2
        ./channel-util -n 1 0x01 0x00 0x02 0x00 0x00 0x00 0xf3 0xf7 0x10 0xff 0xff 0xff 0xff 0xff 0x00 0x23 0x57 0x69 0x64 0x67 0x65 0x74 0x41 0x42 0x43 0x44 0x20 0x31 0x30 0x47 0x42 0x20 0x45 0x74 0x68 0x65 0x72 0x6E 0x65 0x74 0x20 0x43 0x6F 0x6E 0x74 0x72 0x6F 0x6C 0x6C 0x65 0x72
        ./channel-util -n 1 0x02 0x01 0x02 0x01 0xaa 0xbb 0xcc 0xdd 0x00 0x11 0x22 0x33 0x4 0x5
        ./channel-util -n 1 0x03 0x02 0x02 0x02 1 1 0 0 0x00 0x23 0x57 0x69 0x64 0x67 0x65 0x74 0x41 0x42 0x43 0x44 0x20 0x31 0x30 0x47 0x42 0x20 0x45 0x74 0x68 0x65 0x72 0x6E 0x65 0x74 0x20 0x43 0x6F 0x6E 0x74 0x72 0x6F 0x6C 0x6C 0x65 0x72
        ./channel-util -n 1 0x1f 0x13 0x02 0x13 0xff 0x32
        ./channel-util -n 1 0x1f 0x1a 0x02 0x1a 0x00 0x04
        ./channel-util -n 1 0x01 0x1c 0x02 0x1c 0x01 0x01 0x00 0x04 0xf3 0xf7 0x10 0xff
        ./channel-util -n 1 0x02 0x29 0x02 0x29 0x00 0x01 0x00 0x00 0x00 0x00
        ./channel-util -n 1 0x03 0x2a 0x02 0x2a 0x00 0xa0 0x00 0xff 0x00 0x80 0x00 0x50 0x00 0x0f 0xff 0xff 0x00 0x20 0x00 0x15 1 2 3 4

        channel-util -w 1 3 0x2a

        '''
        # clear intial state for all channels to be tested.
        self.run(ncsi_cmdstring='clear initial state', channel_id=0)
        self.run(ncsi_cmdstring='clear initial state', channel_id=1)
        self.run(ncsi_cmdstring='clear initial state', channel_id=2)
        self.run(ncsi_cmdstring='clear initial state', channel_id=3)
        self.run(ncsi_cmdstring='clear initial state', channel_id=0x1f)

        args.pop('test')
        for cmd in self.ncsi_commands:
            args['ncsi_cmdstring'] = cmd

            self.run(**args)

            # after reset channel, clear intial state must be called
            if cmd == 'reset channel':
                self.run(ncsi_cmdstring='clear initial state')


    def prep_ncsi_header(self):
        # start of packet header
        self.packet_header = list()

        # MC_ID, HDR_RV, RESV, IID ...
        self.packet_header.append(self.mc_id)                 # MC_ID,
        self.packet_header.append(self.hrd_rv)                # HDR_RV
        self.packet_header.append("0")                        # RSVD
        self.packet_header.append(self.iid)                   # IID
        self.packet_header.append(self.command)               # CMD
        self.packet_header.append(self.channel_id)            # CHANNEL_ID
        self.packet_header.extend(self.parsed_pay_len)        # PAYLOAD_LEN[12:8], PAYLOAD_LEN[7:0]
        self.packet_header.extend(["0"] * 8)                  # RSVD[63:0]

    def prep_mctp_header(self):
        self.packet_header = list()

    def prep_pldm_header(self):
        self.packet_header = list()

    def print_sent(self):
        self.sent = dict()

        self.sent['mc_id'] = self.mc_id
        self.sent['hrd_rv'] = self.hrd_rv
        self.sent['iid'] = self.iid
        self.sent['command'] = self.command
        self.sent['channel_id'] = self.channel_id
        self.sent['pay_len'] = self.parsed_pay_len
        self.sent['payload'] = self.payload
        self.sent['checksum'] = self.checksum

        self.pretty(self.sent)

    def stringfy(self):
        self.bus = str(self.bus)
        self.dst_eid = str(self.dst_eid)
        self.msg_type = str(self.msg_type_keys[self.msg_type])
        self.slave_addr = str(hex(self.slave_addr))
        self.mc_id = str(self.mc_id)
        self.hrd_rv = str(self.hrd_rv)
        self.iid = str(hex(self.iid))
        self.command = str(hex(self.command))
        self.channel_id = str(hex(self.channel_id))

    def run(self, verbose=True, bus=3, dst_eid=0, msg_type='NCSI', cml_decode_response=True,
            slave_addr=0x55, mc_id=0, hrd_rv=1, iid=1, command=0, channel_id=0, pay_len=0,
            payload=None, ncsi_cmdstring=None):
        self.verbose             = verbose

        self.cml_decode_response = cml_decode_response
        self.payload             = payload

        self.bus                 = bus
        self.dst_eid             = dst_eid
        self.msg_type            = msg_type
        self.msg_type_str        = msg_type
        self.slave_addr          = slave_addr
        self.mc_id               = mc_id
        self.hrd_rv              = hrd_rv
        self.iid                 = iid
        self.command             = command
        self.channel_id          = channel_id
        self.pay_len             = pay_len


        self.ncsi_cmdstring = ncsi_cmdstring

        # override variables if cmd_string is defined
        if self.msg_type == 'NCSI' and self.ncsi_cmdstring in self.ncsi_commands:
            for k in self.ncsi_commands[self.ncsi_cmdstring]:
                setattr(self, k, self.ncsi_commands[self.ncsi_cmdstring][k])

        # all self attrs are string based for subprocess.run(), multi-byte attrs are list of strings
        self.stringfy()
        self.parsed_pay_len = self.dec_to_2_hex_str(int(self.pay_len))

        # prepare the sent command
        cmd = ["mctp-util"]

        # decode response
        if self.cml_decode_response:
            cmd.append("-d")

        # slave address
        if self.slave_addr:
            cmd.extend(["-s", self.slave_addr])

        # <bus> <dst_eid> <type>
        cmd.extend([self.bus, self.dst_eid, self.msg_type])

        # prepare header
        if self.msg_type_str == 'NCSI':
            self.prep_ncsi_header()
        elif self.msg_type_str == 'MCTP':
            self.prep_mctp_header()
        elif self.msg_type_str == 'PLDM':
            self.prep_pldm_header()
        else:
            sys.exit("wrong or unsupported msg_type")

        # add (NCSI) packet header
        if self.msg_type_str == 'NCSI':
            cmd.extend(self.packet_header)

        # payload
        if self.payload:
            self.payload = self.payload.split(' ')
            cmd.extend(self.payload)
        else:
            if self.pay_len:
                self.payload = ["0"] * self.pay_len
                cmd.extend(self.payload)

        # payload padding for NCSI
        if self.msg_type_str == 'NCSI':
            cmd.extend(['0']*self.payload_padding_len)

        # checksum for NCSI
        if self.msg_type_str == 'NCSI':
            cmd.extend(self.checksum.split(' '))

        if verbose:
            print()

            if int(self.msg_type) == self.msg_type_keys['NCSI'] and self.ncsi_cmdstring in self.ncsi_commands:
                print("Running NCSI Example:", self.ncsi_cmdstring)
            #elif mctp_cmdstring in self.mctp_

            print("Excuting: " + " ".join(cmd))
            print("Command sent:")

            self.print_sent()
        try:
            #res = subprocess.run(["python", "-c", "\"print(123)\""], capture_output=True, text=True)
            #res = subprocess.run(["dir"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.res = subprocess.run(cmd, capture_output=True, text=True)
            #print(res.stderr)
            #print("-------------")
        except subprocess.CalledProcessError as e:
            print(e.output)

        if int(self.msg_type) == self.msg_type_keys['NCSI']:
            self.parse_ncsi()
        elif int(self.msg_type) == self.msg_type_keys['MCTP']:
            self.parse_mctp()

        if self.verbose:
            print("Response:")
            self.pretty(self.response)

    def parse_ncsi(self):
        self.response = dict()

        # get raw reponse line
        response_lines = self.res.stdout.splitlines()

        for i, l in enumerate(response_lines):
            if "raw response" in l:
                self.raw_response = response_lines[i+1]
                break

        if not self.raw_response:
            sys.exit("Command failed to have a raw reponse in stdout")
        self.raw_response_list = self.raw_response.split(' ')

        # assign MC_ID, HDR_RV, .... PAYLOAD_LEN, single byte vals
        for i, val in enumerate(self.raw_response_list):
            if i < len(self.ncsi_fixed_val_keys):
                self.response[self.ncsi_fixed_val_keys[i]] = val
            else:
                break

        self.response['PayLen'] = self.raw_response_list[i:i+10]
        self.response['ResponseCode'] = self.raw_response_list[i+10:i+12]
        self.response['ResponseReason'] = self.raw_response_list[i+12:i+14]
        self.response['Payload'] = self.raw_response_list[i+14:]

        if self.ncsi_cmdstring in self.ncsi_res_parser:
            self.response['NCSI Payload Parser'] = dict()

            for k, v in self.ncsi_res_parser[self.ncsi_cmdstring].items():
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



    def parse_mctp(self):
        self.response = dict()
        self.response = dict()

        # get raw reponse line
        response_lines = self.res.stdout.splitlines()

        for i, l in enumerate(response_lines):
            if "raw response" in l:
                self.raw_response = response_lines[i+1]
                break

        if not self.raw_response:
            sys.exit("Command failed to have a raw reponse in stdout")
        self.raw_response_list = self.raw_response.split(' ')

        for i, val in enumerate(self.raw_response_list):
            if i < len(self.mctp_fixed_val_keys):
                self.response[self.mctp_fixed_val_keys[i]] = val
            else:
                break

        self.response['response data'] = self.raw_response_list[i:]


    def verify(self):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # @note default vals should be the same as default vals in run() so that
    #       both command line and python api behave the same
    parser.add_argument('-w', '--wrapper', help='Which wrapper to use', required=True)
    parser.add_argument('-v', '--verbose', help='Verbose', action='store_true')
    parser.add_argument('-t', '--test', help='Test all NCSI commands', action='store_true')
    parser.add_argument('--bus', help='', type=int, default=3, required=False)
    parser.add_argument('--dst_eid', help='', type=int, default=0, required=False)
    parser.add_argument('--msg_type', help='', type=str, default='NCSI', required=False)
    parser.add_argument('--cml_decode_response', help='-d tag for mctp-util', type=bool, default=True, required=False)
    parser.add_argument('--slave_addr', help='Slave address', type=int, default=0x55, required=False)
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

    if args['wrapper'] in ('NCSI', 'MCTP', 'PLDM'):
        args.pop('wrapper')
        m = MCTPWrapper()
        if args['test']:
            m.runall(args)
        else:
            args.pop('test')
            m.run(**args)
    elif args['wrapper'] == 'SMBus':
        args.pop('wrapper')
        w = SMBusWrapper()
        w.run()