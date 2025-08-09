import unittest
from src.mcp_server.server import MCPServer

class TestMCPServer(unittest.TestCase):

    def setUp(self):
        self.server = MCPServer()

    def test_server_initialization(self):
        self.assertIsNotNone(self.server)

    def test_server_start(self):
        self.server.start()
        self.assertTrue(self.server.is_running)

    def test_server_stop(self):
        self.server.start()
        self.server.stop()
        self.assertFalse(self.server.is_running)

    def test_register_tool(self):
        tool_name = "TestTool"
        self.server.register_tool(tool_name)
        self.assertIn(tool_name, self.server.get_registered_tools())

    def test_unregister_tool(self):
        tool_name = "TestTool"
        self.server.register_tool(tool_name)
        self.server.unregister_tool(tool_name)
        self.assertNotIn(tool_name, self.server.get_registered_tools())

if __name__ == '__main__':
    unittest.main()