# DjangoProject: Distributed File Storage Simulation

This Django web application simulates a distributed file storage system using chunking and replication.

## Features

- **Chunking & Replication**: Files are split into 1MB chunks, stored on multiple "nodes" (directories), and replicated.
- **Checksum Validation**: Each chunk is verified with SHA256.
- **Fallback**: If the primary chunk is corrupted or missing, the system falls back to the replica.
- **Admin Interface**: Monitor `StoredFile` and `FileChunk` records.
