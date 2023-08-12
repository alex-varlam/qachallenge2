import asyncio
import time
import pytest
import random
import requests
import string
from HoprNode import HoprCluster, HoprNode

hc=None

def setup_module(module):
    global  hc
    hc = HoprCluster()
    hc.populate_cluster_information()
    time.sleep(1)

@pytest.mark.parametrize("node_s, node_d, msg",[("node1","node5","test123"),("node3","node5","BlaBla"),("node2","node1","aleX!3 53$"),("node2","node3","#@$%")])
def test_hopr_send_message_happy_path(node_s, node_d, msg):
    """ test send message for different values of valid messages -text, uppercase and lowercase, string and numbers, special chars.
    Check messages are received on the destination node"""
    asyncio.run(hc.send_message(node_s, node_d, msg))
    time.sleep(1)
    print(f"Did i get an ack for my message? {hc.nodes_dict[node_s].received_messages}")
    print(f"Did i get the message on the destination node? {hc.nodes_dict[node_d].received_messages}")
    assert msg in hc.nodes_dict[node_d].received_messages[-1]
    time.sleep(1)

def test_hopr_send_message_special_alphabet():
    msg = "El Niño"
    asyncio.run(hc.send_message("node4", "node1", msg))
    time.sleep(1)
    expected_message = str(msg.encode("UTF-8"))[2:-1]
    assert expected_message in hc.nodes_dict["node1"].received_messages[-1]

async def send_multiple_messages_same_source():
    await asyncio.gather(hc.send_message("node1", "node3", "test1"), hc.send_message("node2", "node3", "test2"))

def test_hopr_send_multiple_messages_same_source():
    """test sending messages at the same time from 2 different sources to the same destination node. Check messages
    are received."""
    asyncio.run(send_multiple_messages_same_source())
    time.sleep(2)
    print(hc.nodes_dict["node3"].received_messages)
    print(hc.nodes_dict["node1"].received_messages)
    print(hc.nodes_dict["node2"].received_messages)
    found_msg1 = any(["test1" in msg for msg in hc.nodes_dict["node3"].received_messages])
    found_msg2 = any(["test2" in msg for msg in hc.nodes_dict["node3"].received_messages])
    assert all([found_msg1,found_msg2])==True
    time.sleep(1)

def test_hopr_send_message_with_path():
    """ test sending message is successful when specifying the path attribute as a list of a valid peer."""
    peer_id = hc.nodes_dict["node5"].find_peer_id(hc.nodes_dict["node4"])
    asyncio.run(hc.send_message("node5", "node4", "alex1277433", peer_id))
    time.sleep(1)
    print(f"Did i get an ack for my message? {hc.nodes_dict['node5'].received_messages}")
    print(f"Did i get the message on the destination node? {hc.nodes_dict['node4'].received_messages}")
    time.sleep(1)
    assert "alex1277433" in hc.nodes_dict["node4"].received_messages[-1]

def test_hopr_send_message_node_not_defined():
    """ test send message when node is not defined in config.yaml. tests specifically the python wrapper."""
    with pytest.raises(Exception) as e_info:
        asyncio.run(hc.send_message("node1", "bogus_node", "alex"))
    assert "Incomplete node information! Please check config and try again!" in f"{e_info}"

def test_hopr_send_message_node_not_found():
    """ test send message when destination node is not in the list of peers connected or announced. tests specifically the python wrapper."""
    bogus_node = HoprNode(1234)
    bogus_node._announced_address_list=["whatever"]
    hc.nodes_dict["bogus_node"] = bogus_node
    with pytest.raises(Exception) as e_info:
        asyncio.run(hc.send_message("node1", "bogus_node", "alex"))
    assert "There is no matching peer announced or connected matching this node address!" in f"{e_info}"

def test_hopr_send_message_too_long():
    """ test sending message that is too long with a valid source node and destination node. Validate status code and error message."""
    chars = string.ascii_letters + string.digits
    rand_string = "".join(random.choice(chars) for _ in range(1024))
    with pytest.raises(Exception) as e_info:
        asyncio.run(hc.send_message("node1", "node4", rand_string))
    assert 'Unable to send message! Got 422 with error {"status":"UNKNOWN_FAILURE","error":"Message does not fit into one packet. Please split message into chunks of 500 bytes"}' in f"{e_info}"

def test_hopr_send_message_invalid_path():
    """ test sending message by specifying a bogus path to the destination. Validate status code and error message."""
    with pytest.raises(Exception) as e_info:
        asyncio.run(hc.send_message("node1", "node4", "alex", "bogus path"))
    assert 'Unable to send message! Got 400 with error {"status":"INVALID_INPUT"}' in f"{e_info}"

def test_hopr_send_message_wrong_recipient():
    """ test sending message to an invalid peer. Validate status code and error message."""
    url, headers, data = hc.nodes_dict["node4"].construct_request_for_sending_message("test123", hc.nodes_dict["node3"])
    data["recipient"]+="fff"
    result = requests.post(url, headers=headers, json=data)
    assert result.status_code == 400
    assert result.json() == {"status":"INVALID_ADDRESS"}

def test_hopr_send_message_multiple_recipients():
    """ test sending a message to multiple peers. Validate error status code and error message."""
    url, headers, data = hc.nodes_dict["node1"].construct_request_for_sending_message("test123", hc.nodes_dict["node2"])
    peer_id= hc.nodes_dict["node1"].find_peer_id(hc.nodes_dict["node3"])
    data["recipient"] = [data["recipient"], peer_id]
    data["path"] = []
    result = requests.post(url, headers=headers, json=data)
    assert result.status_code == 400
    assert result.json() == {"status":"INVALID_ADDRESS"}

@pytest.mark.parametrize("hops_value",[(53),("sdaasda"),(-1),(0),("#$%^&&")])
def test_hopr_send_message_incorrect_number_of_hops(hops_value):
    """ test sending message with incorrect number of hops. Validate status code and error message."""
    url, headers, data = hc.nodes_dict["node1"].construct_request_for_sending_message("test123", hc.nodes_dict["node3"])
    data["hops"] = hops_value
    result = requests.post(url, headers=headers, json=data)
    assert result.status_code == 400
    assert result.json() == {"status": "INVALID_INPUT"}

def test_hopr_send_message_no_hops():
    """ test sending a message is successful when hops is not included in the request body. """
    url, headers, data = hc.nodes_dict["node5"].construct_request_for_sending_message("1223434", hc.nodes_dict["node3"])
    data.pop("hops")
    result = requests.post(url, headers=headers, json=data)
    assert result.status_code == 202

@pytest.mark.parametrize("missing_elem",[("recipient"),("body")])
def test_hopr_send_message_missing_data_in_request_body(missing_elem):
    """ test sending a message returns the correct error message when mandatory attributes are missing from the
    request body: destination peer and message."""
    error_json = {"status": "INVALID_INPUT"} if missing_elem !="recipient" else {"status":"INVALID_ADDRESS"}
    url, headers, data = hc.nodes_dict["node4"].construct_request_for_sending_message("test123", hc.nodes_dict["node3"])
    data.pop(missing_elem)
    result = requests.post(url, headers=headers, json=data)
    assert result.status_code == 400
    assert result.json() == error_json

def test_hopr_send_message_empty_path():
    """ test sending message is successful when specifying the path attribute as an empty list."""
    url, headers, data = hc.nodes_dict["node5"].construct_request_for_sending_message("alex", hc.nodes_dict["node3"])
    data["path"] = []
    result = requests.post(url, headers=headers, json=data)
    assert result.status_code == 202

def test_authentication_failure():
    """ test correct error is returned in case of authentication failure."""
    url, headers, data = hc.nodes_dict["node2"].construct_request_for_sending_message("a b c d", hc.nodes_dict["node3"])
    headers["x-auth-token"] += "random_string"
    result = requests.post(url, headers=headers, json=data)
    assert result.status_code == 401
    assert result.json() == {"status":"UNAUTHORIZED","error":"authentication failed"}