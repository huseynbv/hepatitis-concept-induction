from owlready2 import *
import owlready2
owlready2.JAVA_EXE = r"/usr/lib/jvm/java-25-openjdk/bin/java"

onto = get_ontology("http://test.org/onto.owl")
with onto:
    class Person(Thing): pass
    class Student(Person): pass
    s = Student("elvin")

#sync_reasoner()  # this is the step that needs Java
print(Person.instances())
print(list(onto.classes()))
