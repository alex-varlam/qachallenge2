## QA Challenge HOPR

Below you can find a brief description of my approach for solving the [testing challenge](https://github.com/hoprnet/testing-challenge) including 
how to setup the environment, how to run the tests and the types of tests included and the possible test types not supported.
Project contents (more details below):
- HoprNode.py - python wrapper implementation for sending a message from one node to the other. 
- hopr_cluster_config.yaml - a yaml which describes the cluster and the nodes inside. 
- test_hopr.py - tests for sending message functionality 
- requirements.txt - python packages to be installed to be able to run the tests.
- README.md

### Test Environment
- pull docker image from gcr.io/hoprassociation/hopr-pluto:1.92.7
- run docker image also publishing the exposed ports in the dockerfile 
```shell
    docker run --rm -d -p 13301-13305:13301-13305 -p 19091-19095:19091-19095 -p 18081-18085:18081-18085 --name pluto_cluster gcr.io/hoprassociation/hopr-pluto:1.92.7
```
- install [python](https://www.python.org/downloads/) (minimum version 3.10)
- install python packages
  - Windows:
```shell
    python -m pip install -r requirements.txt
```
  - MacOS/Linux:
```shell
    pip3 install -r requirements.txt
```
- (Optional) Adjust hopr_config_config.yaml

Config yaml contains information about the mini cluster as defined in the [dockerFile](https://github.com/hoprnet/hoprnet/blob/master/scripts/pluto/Dockerfile). 
In case of changes to the dockerfile or overidding params in the docker run command, please make sure to reflect those changes in the yaml as well. 

### Running the tests

Please make sure to wait a few minutes between running the tests and running the docker image. It will give the time 
for peer information to be populated across all nodes.
Download the files HoprNode.py and test_hopr.py. Go to the download directory and execute:

```shell
pytest test_hopr.py -v
```
You should see an output similar to
``` shell
test_hopr.py::test_hopr_send_message_happy_path[node1-node2-alex] PASSED                                                                                                                                                                                                                                                                                                                                                                                                         [  5%]
test_hopr.py::test_hopr_send_message_happy_path[node3-node5-BlaBla] PASSED                                                                                                                                                                                                                                                                                                                                                                                                       [ 11%]
test_hopr.py::test_hopr_send_message_happy_path[node1-node5-alex23 53$] PASSED                                                                                                                                                                                                                                                                                                                                                                                                   [ 17%]
test_hopr.py::test_hopr_send_message_happy_path[node2-node3-# @$%] PASSED                                                                                                                                                                                                                                                                                                                                                                                                        [ 23%]
test_hopr.py::test_hopr_send_message_node_not_defined PASSED                                                                                                                                                                                                                                                                                                                                                                                                                     [ 29%] 
test_hopr.py::test_hopr_send_message_node_not_found PASSED                                                                                                                                                                                                                                                                                                                                                                                                                       [ 35%] 
test_hopr.py::test_hopr_send_message_too_long PASSED                                                                                                                                                                                                                                                                                                                                                                                                                             [ 41%]
test_hopr.py::test_hopr_send_message_invalid_path PASSED                                                                                                                                                                                                                                                                                                                                                                                                                         [ 47%]
test_hopr.py::test_hopr_send_message_wrong_recipient PASSED                                                                                                                                                                                                                                                                                                                                                                                                                      [ 52%]
test_hopr.py::test_hopr_send_message_multiple_recipients PASSED                                                                                                                                                                                                                                                                                                                                                                                                                  [ 58%]
test_hopr.py::test_hopr_send_message_incorrect_number_of_hops PASSED                                                                                                                                                                                                                                                                                                                                                                                                             [ 64%] 
test_hopr.py::test_hopr_send_message_no_optional_attributes[hops] PASSED                                                                                                                                                                                                                                                                                                                                                                                                         [ 70%]
test_hopr.py::test_hopr_send_message_no_optional_attributes[path] PASSED                                                                                                                                                                                                                                                                                                                                                                                                         [ 76%]
test_hopr.py::test_hopr_send_message_missing_data_in_request_body[recipient] PASSED                                                                                                                                                                                                                                                                                                                                                                                              [ 82%] 
test_hopr.py::test_hopr_send_message_missing_data_in_request_body[body] PASSED                                                                                                                                                                                                                                                                                                                                                                                                   [ 88%]
test_hopr.py::test_hopr_send_message_empty_path PASSED                                                                                                                                                                                                                                                                                                                                                                                                                           [ 94%]
test_hopr.py::test_authentication_failure PASSED                                                                                                                                                                                                                                                                                                                                                                                                                                 [100%] 

=====================================================================================================================
```
### Implementation approach

The python wrapper contains a HoprNode class which is used to get information about the current node, finding peers, 
the send message functionality and receiving incoming messages on the current node. 
To find a peer, it uses the announced address list to identify it in the list of peers. 
To stream incoming messages, it opens a websocket client on a separate thread and stores the messages in a list.
Since there was no clear way to reference the nodes (that I could tell), I created a helper yaml and HoprCluster class 
which allowed to reference the nodes by a "node1", "node2" etc. as defined in the yaml and instantiates a HoprNode 
object for each node in the config. So in the end, you are left with a send message function that takes as arguments 
the "names" of the nodes and the message you want to send.

### Testplan

The current implementation includes tests for:
- positive scenarios:
  - sending different messages from one node to another containing uppercase,lowercase letters, numbers, special characters, spaces
  - sending message with an empty path, or a valid one
  - sending a message without the hops attributes in the request body
  - sending multiple messages at the same time to the same node and checking they are received. 
- negative scenarios:
  - send message to a node that does not exist
  - send message with an invalid path
  - send message with an incorrect number of hops
  - send message without specifying the message
  - sending a message over 500bytes
  - send message with a missing recipient
  - send a message to multiple recipients
  - send message with an incorrect api token
- not included - since in the mini-cluster all the nodes are directly connected there were a few scenarios not included:
  - sending a message to a remote peer and severing the path somewhere along the way
  - sending a large number of messages through the same path
  - testing whether the optimal path is used - in case of multiple paths available with different number of hops - send 
a message without specifying the path and checking which one is used.
  - testing the time required to find a path in a complex scenario of large number of nodes.