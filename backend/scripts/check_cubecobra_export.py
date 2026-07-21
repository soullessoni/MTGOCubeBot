from app.services.cubecobra.client import CubeCobraClient


client = CubeCobraClient(
    "https://cubecobra.com/cube/list/"
    "82f27ca5-58ff-4874-84da-7f8bc23e2073"
)

export = client.download_mtgo_export()

print(export[:2000])
