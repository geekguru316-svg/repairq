import copy

class Base:
    def __init__(self):
        self.dicts = [1]
    
    def __copy__(self):
        print("Copying Base")
        # This is what Django does
        duplicate = copy.copy(super())
        duplicate.dicts = self.dicts[:]
        return duplicate

class Child(Base):
    pass

c = Child()
try:
    c2 = copy.copy(c)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
