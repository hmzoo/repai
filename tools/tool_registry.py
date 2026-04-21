class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register_tool(self, name, func):
        if not callable(func):
            raise ValueError(f"Tool '{name}' must be a callable function.")
        self._tools[name] = func

    def get_tool(self, name):
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry.")
        return self._tools[name]

    def list_tools(self):
        return list(self._tools.keys())

# Global instance of the tool registry
tool_registry = ToolRegistry()
