import threading
import select
import time
import requests
import yaml
import websocket
import asyncio
import websockets
import numpy as np

class CustomException(Exception):
    """Custom error class to allow for more spcific error messages"""
    def __call__(self, *args):
        return self.__class__(*(self.args + args))

    def __str__(self):
        return ":".join(self.args)

class HoprNode:
    api_token = "%th1s-IS-a-S3CR3T-ap1-PUSHING-b1ts-TO-you%"
    def __init__(self, api_port):
        self.api_port = api_port
        self.base_url = f"http://localhost:{self.api_port}/api/v2"
        self.headers = {
            "Accept": "application/json",
            "x-auth-token": self.api_token
        }
        self.quality = None
        self.thread = None
        self.event = threading.Event()
        self._peers_info = None
        self._announced_address_list = None
        self.received_messages = []
        self.error = CustomException("HOPR Node Error")
        self.start_listening()

    @property
    def announced_address_list(self):
        """ Gets the node info and stores the node announced address. To be used later to identify peers. """
        if self._announced_address_list:
            return self._announced_address_list
        url = f"{self.base_url}/node/info"
        result = requests.get(url, headers=self.headers)
        if result.status_code != 200:
            raise self.error(f"Something went wrong getting node info! "
                             f"Got status code {result.status_code} and {result.text}")
        self._announced_address_list= result.json()["announcedAddress"]
        return self._announced_address_list

    @property
    def peers_info(self):
        """ Gets a list of peers for the current node storing the peer id and whether it's connected or announced. """
        if self._peers_info:
            return self._peers_info
        self._peers_info = {}
        url = f"{self.base_url}/node/peers"
        if self.quality:
            url+=f"?quality={self.quality}"
        result = requests.get(url, headers=self.headers)
        if result.status_code != 200:
            raise self.error(f"Something went wrong getting peer nodes! "
                             f"Got status code {result.status_code} and {result.text}")
        for elem in result.json()["connected"]:
            self._peers_info[elem["peerId"]] = {
                "address": elem["multiAddr"],
                "type": "connected"
            }
        for elem in result.json()["announced"]:
            if elem["peerId"] not in self._peers_info:
                self._peers_info[elem["peerId"]] = {
                    "address": elem["multiAddr"],
                    "type": "announced"
                }
        return self._peers_info

    def find_peer_id(self, hopr_object):
        """ Based on an instance of the hopr object given as an argument it will search through the list of peers for
        the corresponding announced address and retrieves the peer id."""
        for peer_id, peer_info in self.peers_info.items():
            if peer_info["address"] in hopr_object.announced_address_list:
                return peer_id
        raise self.error(f"There is no matching peer announced or connected matching this node address! "
                         f"{hopr_object.announced_address_list}")

    def construct_request_for_sending_message(self, msg, hopr_object, path=None):
        """ helper function for sending a message. Constructs the information to be used in the POST message.
        msg = message to be send
        hopr_object = instance of the destination node object
        path = optional path to the destination node."""
        url = f"{self.base_url}/messages/"
        headers = self.headers
        headers["Content Type"] = "application/json"
        destination_peer_id = self.find_peer_id(hopr_object)
        data = {
            "body": msg,
            "recipient": destination_peer_id,
            "hops": 1
        }
        if path:
            data["path"] = [path]
            data["hops"] = len(data["path"])
        return url, headers, data

    def send_message(self, msg, hopr_object, path=None):
        """ Sends a message from the current node to the desired node given as an instance of the hopr object."""
        url, headers, data = self.construct_request_for_sending_message(msg, hopr_object, path)
        result = requests.post(url, headers=headers, json=data)
        if result.status_code != 202:
            raise self.error(f"Unable to send message! Got {result.status_code} with error {result.text}")
        return f"Message sent successfully! Got {result.text}"

    async def call_message_websocket(self):
        """ read incoming messages received on node. try to store them in a more ledgible way."""
        async with websockets.connect(
                    f"ws://127.0.0.1:{self.api_port}/api/v2/messages/websocket/?apiToken={self.api_token}") as websocket:
            while True:
                response = await websocket.recv()
                try:
                    arr = np.array([int(x) for x in response.split(",")], dtype=np.uint8)
                    resp = arr.view(f'S{arr.shape[0]}')
                except:
                    resp = response
                self.received_messages.append(str(resp))

    def thread_handler_receive(self):
        self.loop= asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.call_message_websocket())

    def start_listening(self):
        self.thread = threading.Thread(target=self.thread_handler_receive, daemon=True)
        self.thread.start()

class HoprCluster:
    def __init__(self, config_file = "hopr_cluster_config.yaml"):
        """ Config file contains information about the HOPR cluster. the node list with details for each node
        - mandatory api_port"""
        self.config_file = config_file
        self.nodes_dict = {}
        self.error = CustomException("HOPR Cluster Error")

    def populate_cluster_information(self):
        """ parses yaml and creates a HOPR node object for each node that can be referenced by using the node name."""
        with open(self.config_file, "r", encoding="utf-8") as f:
            node_cluster_details = yaml.safe_load(f)
        if "api_token" in node_cluster_details and node_cluster_details["api_token"] != HoprNode.api_token:
            HoprNode.api_token = node_cluster_details["api_token"]
        if "nodes_list" not in node_cluster_details:
            raise self.error(f"Missing node list information for cluster! Check {self.config_file}")
        for node_name, node_details in node_cluster_details["nodes_list"].items():
            if "api_port" not in node_details:
                raise self.error(f"Missing api port for node {node_name} in {self.config_file}")
            self.nodes_dict[node_name]= HoprNode(node_details["api_port"])

    async def send_message(self, node_name_source, node_name_dest, msg, path=None):
        """ sends a message based on the source node name and the destination node name. """
        if node_name_source not in self.nodes_dict or node_name_dest not in self.nodes_dict:
            raise self.error("Incomplete node information! Please check config and try again!")
        print(self.nodes_dict[node_name_source].send_message(msg, self.nodes_dict[node_name_dest], path))



# if __name__ == "__main__":
#     hc = HoprCluster()
#     hc.populate_cluster_information()
#     time.sleep(1)
#     peer_id = hc.nodes_dict["node1"].find_peer_id(hc.nodes_dict["node3"])
#     asyncio.run(hc.send_message("node1", "node3", "alex", peer_id))
    # h1 = HoprNode(13301)
    # h2 = HoprNode(13302)
    # h3 = HoprNode(13303)
    # h2.start_listening()
    # h1.send_message("alex",h2)
    # time.sleep(2)
    # h3.send_message("blabla",h2)
    # time.sleep(5)
    # # h2.receive_message()
    # print(h2.received_messages)