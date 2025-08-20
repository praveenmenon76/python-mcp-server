class Tool:
    def __init__(self, name, description, version):
        self.name = name
        self.description = description
        self.version = version

    def __repr__(self):
        return f"Tool(name={self.name}, description={self.description}, version={self.version})"


class ToolModel:
    def __init__(self):
        self.tools = []

    def add_tool(self, tool):
        self.tools.append(tool)

    def get_tools(self):
        return self.tools

    def find_tool_by_name(self, name):
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
