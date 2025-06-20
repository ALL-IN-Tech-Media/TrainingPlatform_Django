class A:
    def method(self):
        print(111)

class B:
    def method(self):
        print(222)

class C(B, A):
    def mmm(self):
        print(1333)


c = C()
c.method()