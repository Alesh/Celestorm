Common protocols
----------------

.. automodule:: celestorm.protocols

    | **P** Generalizes the type of the instruction payload.
    | **U** Generalizes the type of the object identifier.


 .. autoclass:: Entity(Protocol[U])
      :members:

 .. autoclass:: Instruction(Protocol[P, U])
      :members:
      :member-order: bysource

 .. autoclass:: Signer(Protocol)
      :members:
      :member-order: bysource

 .. autoclass:: Package(Protocol[P, U])
      :members:
      :member-order: bysource
      :class-doc-from: class
      :special-members: __new__
