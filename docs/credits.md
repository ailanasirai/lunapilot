# Credits

## NASA data and tools

| Resource | Used for |
|---|---|
| NASA JPL / NAIF SPICE kernels (DE421, `moon_pa_de421_1900-2050.bpc`, `moon_080317.tf`, planetary constants) | Sun, Earth and Moon orientation for the engine |
| NASA JPL Horizons | Validation of the engine (see `horizons_validation.txt`) |
| NASA Artemis III candidate landing regions | Region names |

## Software

Skyfield, Streamlit, Plotly, pandas, NumPy, Pillow, jplephem, sgp4, certifi.

## Images (Pixabay)

Images are from [Pixabay](https://pixabay.com) and used under the Pixabay Content License. Authors:

| File in `app/assets/` | Author on Pixabay |
|---|---|
| earth.jpg | wikiimages |
| sun.jpg (not used in the app) | wikiimages |
| moon.jpg, moon_close.jpg | jwvein, bellergy |
| nebula.jpg | timrael |
| lander.jpg | cristianis |

## Use of AI

Claude (Anthropic) assisted with parts of the code, the unit tests and the documentation. All numbers come from our own engine and NASA data and were checked against NASA JPL Horizons by the team.