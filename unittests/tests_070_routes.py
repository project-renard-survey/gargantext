"""
ROUTE UNIT TESTS
================
"""
from django.test import TestCase
from django.test import Client

# to be able to create Nodes
from gargantext.models import Node

# to be able to compare in test_073_get_api_one_node()
from gargantext.constants import NODETYPES

# provides GargTestRunner.testdb_session
from unittests.framework import GargTestRunner


class RoutesChecker(TestCase):
    def setUp(self):
        """
        Will be run before each test
        """
        self.client = Client()

        # login with our fake user
        response = self.client.post(
                            '/auth/login/',
                            {'username': 'pcorser', 'password': 'peter'}
                            )
        print(response.status_code)

        session = GargTestRunner.testdb_session

        new_project = Node(
            typename = 'PROJECT',
            name = "hello i'm a project",
        )
        session.add(new_project)
        session.commit()
        self.a_node_id = new_project.id
        print("created a project with id: %i" % new_project.id)

    def test_071_get_front_page(self):
        ''' get the front page / '''
        front_response = self.client.get('/')
        self.assertEqual(front_response.status_code, 200)
        self.assertIn('text/html', front_response.get('Content-Type'))
        # on suppose que la page contiendra toujours ce titre
        self.assertIn(b'<h1>Gargantext</h1>', front_response.content)

    def test_072_get_api_nodes(self):
        ''' get "/api/nodes" '''
        api_response = self.client.get('/api/nodes')
        self.assertEqual(api_response.status_code, 200)

        # 1) check the type is json
        self.assertTrue(api_response.has_header('Content-Type'))
        self.assertIn('application/json', api_response.get('Content-Type'))

        # 2) let's try to get things in the json
        json_content = api_response.json()
        json_count = json_content['count']
        json_nodes = json_content['records']
        self.assertEqual(type(json_count), int)
        self.assertEqual(type(json_nodes), list)
        print("\ntesting nodecount: %i " % json_count)


    def test_073_get_api_one_node(self):
        ''' get "api/nodes/<node_id>" '''

        # we first get one node id by re-running this bit from test_072
        a_node_id = self.client.get('/api/nodes').json()['records'][0]['id']

        one_node_route = '/api/nodes/%i' % a_node_id
        # print("\ntesting node route: %s" % one_node_route)
        api_response = self.client.get(one_node_route)
        self.assertTrue(api_response.has_header('Content-Type'))
        self.assertIn('application/json', api_response.get('Content-Type'))

        json_content = api_response.json()
        nodetype = json_content['typename']
        nodename = json_content['name']
        print("\ntesting nodename:", nodename)
        print("\ntesting nodetype:", nodetype)
        self.assertIn(nodetype, NODETYPES)

    # TODO http://localhost:8000/api/nodes?types[]=CORPUS

    # £TODO test request.*
        # print ("request")
        # print ("user.id", request.user.id)
        # print ("user.name", request.user.username)
        # print ("path", request.path)
        # print ("path_info", request.path_info)
