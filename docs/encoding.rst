Data encoding and packaging
---------------------------
.. automodule:: celestorm.encoding

    .. autoclass:: celestorm.encoding.Instruction(Generic[U], ABC)
        :members:
        :member-order: bysource

    .. autoclass:: celestorm.encoding.Package(Protocol[U], Buffer, ABC)
        :members:
        :member-order: bysource


Data encoding protocols
"""""""""""""""""""""""
.. automodule:: celestorm.encoding.protocols

    .. autoclass:: celestorm.encoding.protocols.Entity(Protocol[U])
        :members:
        :member-order: bysource

    .. autoclass:: celestorm.encoding.protocols.Hasher(Protocol[U])
        :members:
        :member-order: bysource

    .. autoclass:: celestorm.encoding.protocols.Signer(Protocol[U])
        :members:
        :member-order: bysource