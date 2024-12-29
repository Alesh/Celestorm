Celestorm
=========

Celestorm is a Python package that enables the design of a part of a distributed
application as an execution layer for modular blockchains. This functionality,
combined with the use of modern blockchains (such as Avail, Celestia, Near DA,
etc.) that support a data availability layer (DA-layer), simplifies the creation
of distributed solutions for specific tasks. The package's modules abstract away
blockchain interaction and state management, providing flexibility and platform
independence.

.. toctree::
    :maxdepth: 2
    :caption: Contents:

    Key features <key_features>
    Exception classes <errors>
    Data encoding and packaging <encoding>

Glossary
--------

.. glossary::

    Execution Layer
        The layer of a distributed application responsible for executing
        instructions and modifying the system's state.

    DA-layer (Data Availability Layer)
        A blockchain layer that ensures data availability for all network
        participants.

    Sync Round
        The process of executing instructions within a single package. It is
        determined by an incrementing number calculated using a specific
        algorithm (e.g., (block_height << 16) + tx_index).

    Revision
        The version number of an object, updated with each modification. It
        corresponds to the Sync Round in which the change was recorded.

    Instruction
        A data structure that defines an action to modify the state of
        distributed data.

    OID (Object Identifier)
        A unique identifier of the object with which the instruction interacts.

    Payload
        The data transmitted within an instruction, required to modify the
        object's state.

    Package
        A set of instructions grouped for atomic execution. A package may be
        signed for authenticity verification.

    Atomic Broadcast
        A mechanism that ensures packets are delivered to all nodes in the same
        order.