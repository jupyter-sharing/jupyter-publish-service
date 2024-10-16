# Jupyter Publishing Service

A (backend agnostic) service for publishing sharable Jupyter content.

By default, publishing service uses SQL lite database with asyncIO drivers. The database is used for storing users, file metadata and permissions, collaborators, and also actual files themselves.
It is possible to swap out any or all of these classes as long as the API model and data model is consistent. For example, files could be stored in S3, and SQL lite can be used for file metadata. 
To swap out, content manager use the steps below

```
--JupyterPublishingService.file_manager_class="jupyter_server.services.contents.largefilemanager.AsyncLargeFileManager"
```

Features supported:

- Authorization based on roles and permissions
- Authentication with bearer tokens
- SQL based collaborator store
- SQL based file metadata store
- SQL based file content store

TODO:

- RTC changes
- Unit testing framework

# With pre-built contents managers

Start publishing service with

```
--JupyterPublishingService.file_manager_class="jupyter_server.services.contents.largefilemanager.AsyncLargeFileManager"
```

This will use local file system for storing notebook files

# Getting Started

Set up python virtual environment

Install dependencies with pip

jupyter publishing --JupyterPublishingService.ip="0.0.0.0" --JupyterPublishingService.port=9001
