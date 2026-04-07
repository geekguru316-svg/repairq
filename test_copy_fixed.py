import copy

class Base:
    def __init__(self):
        self.dicts = [1]
        self.other = "test"
    
    def __copy__(self):
        print("Copying Base with fix")
        new_instance = self.__class__.__new__(self.__class__)
        new_instance.__dict__.update(self.__dict__)
        new_instance.dicts = self.dicts[:]
        return new_instance

class Child(Base):
    def __init__(self):
        super().__init__()
        self.child_attr = "child"
    
    def __copy__(self):
        print("Copying Child")
        duplicate = super().__copy__()
        # In Django's Context: duplicate.render_context = copy(self.render_context)
        return duplicate

c = Child()
try:
    c2 = copy.copy(c)
    print(f"Success: {c2.dicts}, {c2.other}, {c2.child_attr}")
    print(f"Is c2 a different object? {c is not c2}")
    print(f"Is dicts a different list? {c.dicts is not c2.dicts}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
