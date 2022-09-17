
import subprocess
import argparse

class MCTPWrapper():
    def __init__(self):


        # TODO: enum in python?
        self.msg_type = {'MCTP': 0, 'PLDM':1, 'NCSI':2, 'ETH':3, 'NVME':4, 'SPDM':5, 'SecMsg':6}
        pass

    def dec_to_2_hex_str(self, dec):
        if dec > 4095:
            raise ValueError("Payload length has 12 bits, can't be more than 4095.")

        # ([12:8] and [7:0])
        return ("0", str(hex(dec))) if dec < 255 else (str(hex(dec-255)), str(hex(255)))

    def run(self, verbose=True, bus=1, dst_eid=0, msg_type='NCSI', decode_response=True,
            slave_addr=55, mc_id=0, hrd_rv=1, iid=1, channel_id=0, pay_len=0):
        parsed_pay_len = self.dec_to_2_hex_str(pay_len)

        cmd = ["mctp-utils"]

        # decode response
        if decode_response:
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
        packet_header.append(str(channel_id))       # CHANNEL_ID
        packet_header.extend(list(parsed_pay_len))  # PAYLOAD_LEN[12:8], PAYLOAD_LEN[7:0]
        packet_header.extend(["0"] * 8)             # RSVD[63:0]

        # add NCSI packet header
        cmd.extend(packet_header)

        if verbose:
            print(" ".join(cmd))

        try:
            res = subprocess.run(["python", "-c", "\"print(123)\""], capture_output=True, text=True)
            #res = subprocess.run(["python", "-c", "\"print(123)\""], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            #res = subprocess.run(["dir"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            #res = subprocess.run(cmd, capture_output=True, text=True)
            print(res.stderr)
            print("-------------")
            print(res.stdout.strip('\n'))
        except subprocess.CalledProcessError as e:
            print(e.output)

    def verify(self):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help='Verbose', required=False)
    parser.add_argument('--slaveaddr', help='Slave address', required=False)
    parser.add_argument('--mcid', help='MC ID', required=False)
    parser.add_argument('--headerrv', help='Header revision', required=False)
    parser.add_argument('--iid', help='IID', required=False)
    args = vars(parser.parse_args())
    m = MCTPWrapper()
    m.run()