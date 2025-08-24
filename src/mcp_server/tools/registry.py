class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.tools_lowercase_map = {}  # Maps lowercase names to actual names

    def register_tool(self, name, tool=None):
        # Check if the tool is already registered (case-insensitive)
        lowercase_name = name.lower()
        if lowercase_name in self.tools_lowercase_map:
            raise ValueError(f"Tool '{name}' is already registered (as '{self.tools_lowercase_map[lowercase_name]}').")
        
        # Store the tool and create a lowercase mapping
        self.tools[name] = tool
        self.tools_lowercase_map[lowercase_name] = name

    def unregister_tool(self, name):
        # Remove from both dictionaries (case-insensitive)
        lowercase_name = name.lower()
        if lowercase_name in self.tools_lowercase_map:
            actual_name = self.tools_lowercase_map[lowercase_name]
            self.tools.pop(actual_name, None)
            self.tools_lowercase_map.pop(lowercase_name, None)
        else:
            # Also try direct removal in case the name is provided exactly
            self.tools.pop(name, None)

    def get_registered_tools(self):
        return list(self.tools.keys())

    def get_tool(self, name):
        # First try exact match
        if name in self.tools:
            return self.tools[name]
        
        # Then try case-insensitive match
        lowercase_name = name.lower()
        if lowercase_name in self.tools_lowercase_map:
            actual_name = self.tools_lowercase_map[lowercase_name]
            return self.tools[actual_name]
        
        return None
