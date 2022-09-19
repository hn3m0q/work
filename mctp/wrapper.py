
from curses import raw
import subprocess
import argparse
from urllib import response

class MCTPWrapper():
    def __init__(self):


        # TODO: enum in python?
        self.msg_type = {'MCTP': 0, 'PLDM':1, 'NCSI':2, 'ETH':3, 'NVME':4, 'SPDM':5, 'SecMsg':6}

        self.ncsi_commands = {'clear initial state':{'iid':0, 'command':0},
                              'select package':{'iid':2, 'command':1},
                              'deselect package':{'iid':3, 'command':2},
                              'enable channel':{'iid':4, 'command':3},
                              'disable channel':{'iid':5, 'command':4},
                              'reset channel':{'iid':6, 'command':5},
                              'enable channel network tx': {'iid':7, 'command':6},
                              'disable channel network rx': {'iid':8, 'command':7},
                              'set link': {'iid':9, 'command':9}, #008} TODO channel_id, paylen[12] paylen[11]
                              'get link status': {'iid':0xa, 'command':0xa},
                              'set vlan filter': {'iid':0xb, 'command':0xb}
        }

        self.fixed_val_keys = ['SRC_ID', 'TAG', 'MSG_TYPE', 'MC_ID', 'HeaderRev', 'Rsv', 'IID',
                               'PacketType', 'Channel']

        self.response = None
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
        if dec > 4095: #TODO actually looks like 13 bits?
            raise ValueError("Payload length has 12 bits, can't be more than 4095.")

        # ([12:8] and [7:0])
        return ("0", str(hex(dec))) if dec < 255 else (str(hex(dec-255)), str(hex(255)))

    def run(self, verbose=True, bus=1, dst_eid=0, msg_type='NCSI', cml_decode_response=True,
            slave_addr=55, mc_id=0, hrd_rv=1, iid=1, command=0, channel_id=0, pay_len=0,
            ncsi_cmdstring=None):
        # override variables if cmd_string is defined
        if ncsi_cmdstring:
            for k in self.ncsi_comands[ncsi_cmdstring]:
                if self.ncsi_comands[ncsi_cmdstring][k]:
                    vars()[k] = self.ncsi_comands[ncsi_cmdstring][k]

        parsed_pay_len = self.dec_to_2_hex_str(pay_len)

        cmd = ["mctp-utils"]

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

        # MC_ID, HDR_RV, RESV, IID
        packet_header.append(str(mc_id))            # MC_ID,
        packet_header.append(str(hrd_rv)),          # HDR_RV
        packet_header.append("0")                   # RSVD
        packet_header.append(str(iid))              # IID
        packet_header.append(str(command))          # CMD
        packet_header.append(str(channel_id))       # CHANNEL_ID
        packet_header.extend(list(parsed_pay_len))  # PAYLOAD_LEN[12:8], PAYLOAD_LEN[7:0]
        packet_header.extend(["0"] * 8)             # RSVD[63:0]

        # add NCSI packet header
        cmd.extend(packet_header)

        if verbose:
            print("Running: " + " ".join(cmd))

        try:
            res = subprocess.run(["python", "-c", "\"print(123)\""], capture_output=True, text=True)
            #res = subprocess.run(["python", "-c", "\"print(123)\""], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            #res = subprocess.run(["dir"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            #res = subprocess.run(cmd, capture_output=True, text=True)
            #print(res.stderr)
            #print("-------------")

            # get raw reponse line
            response_lines = res.stdout.strip('\n')
            for i, l in enumerate(response_lines):
                if "raw response" in l:
                    self.raw_response = response_lines[i+1]
                    break

            self.raw_reponse_list = self.raw_response.split(' ')

            # assign MC_ID, HDR_RV, .... PAYLOAD_LEN, single byte vals
            for i, val in enumerate(self.raw_response_list):
                if i < len(self.fixed_val_keys):
                    self.response[self.fixed_val_keys[i]] = val
                else:
                    break

            self.response['PayLen'] = self.raw_reponse_list[i:i+10]
            self.response['ResponseCode'] = self.raw_reponse_list[i+10:i+12]
            self.response['ResponseReason'] = self.raw_reponse_list[i+12:i+14]
            self.response['Payload'] = self.raw_reponse_list[i+14:]

            # TODO parse for each example
            if ncsi_cmdstring = 'temperature --':
                #self.response[''][''] =
                pass

            if verbose:
                print("Response:")
                self.pretty(self.reponse)

        except subprocess.CalledProcessError as e:
            print(e.output)

    def verify(self):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # @note default vals should be the same as default vals in run() so that
    #       both command line and python api behave the same
    parser.add_argument('-v', '--verbose', help='Verbose', type=bool, default=False, required=False)
    parser.add_argument('--bus', help='', type=int, default=1, required=False)
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
    parser.add_argument('--ncsi_cmdstring', help='A NCSI command string that fills values automatically', type=str, required=False)
    args = vars(parser.parse_args())
    m = MCTPWrapper()
    m.run(**args)