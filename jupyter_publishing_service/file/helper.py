from jupyter_publishing_service.models import JupyterContentsModel


async def create_or_update_jupyter_contents(session, jcm: JupyterContentsModel):
    current_model = await session.get(JupyterContentsModel, jcm.id)
    if current_model is None:
        current_model = jcm
    data = jcm.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(current_model, key, val)
    session.add(current_model)
    await session.commit()
    await session.refresh(current_model)
