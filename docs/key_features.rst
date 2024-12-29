Key Features
------------

The primary task of the execution layer is to synchronously and consistently
change the state of the distributed system. To achieve this, the solution
«Celestorm» introduces several key concepts.

State Change Instructions
"""""""""""""""""""""""""
An instruction is the foundation that defines which object in the distributed
system, under what conditions, and how exactly it should be modified. It consists
of three key components:

* **OID** — a unique identifier of the object to which the instruction applies.
* **Revision** — the version number of the object to which the instruction relates.
* **Payload** — the set of data required to modify the object's state.

Instruction Packages and Sync Round
"""""""""""""""""""""""""""""""""""
Instructions are grouped into packages, which are executed within a single
transaction. Each package accepted for processing is assigned a unique number,
which increments with each new package. Packages are distributed and executed
in strict order according to their numbers.

The process of executing instructions within a single package is called a
**Sync Round**, and the aforementioned number is referred to as the Sync Round
number. A modified object receives a version number (Revision) corresponding
to the Sync Round in which it was changed.

Conditions for Instruction Execution
""""""""""""""""""""""""""""""""""""
Instructions can only be executed if certain conditions are met:

* If the instruction implies modifying or deleting an object's state, the
  object identifier (OID) must match an existing object in the distributed
  system. Additionally, the object's version and the instruction's version
  must be identical.
* If the instruction involves creating a new object, the OID must not match
  any existing object.

At the application level, additional conditions for instruction execution may
be introduced.

.. warning::
    If at least one instruction in the package is invalid, the entire package's
    execution is aborted.

Attributes of Distributed System Objects
""""""""""""""""""""""""""""""""""""""""
From the above definitions and requirements, it follows that objects in the
distributed system, whose states are intended to be modified through the execution
of instruction packages, must have the following attributes:

* **OID** — a unique identifier of the distributed system object.
* **Revision** — the version number of the object (the Sync Round in which its
  last modification occurred).