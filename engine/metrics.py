# Basically takes 2 plain lists of sun and earth elevation angels every 30mins and sumaries them into 4 survival stats
# sunlight_fraction
# earth_visible_fraction
# both_fration
# longest_dark_hours
def compute_metrics(sun_elevation_deg: list[float],earth_elevation_deg: list[float],step_minutes: int = 30,) -> dict[str, float]:
    """
    Calculates power and communication visibility metrics from Sun and Earth
    elevation angle time series.
    """
    # Safety check: if either list is empty, return 0.0 for all metrics
    total_steps = len(sun_elevation_deg)
    if total_steps == 0 or len(earth_elevation_deg) != total_steps:
        return {
            "sunlit_fraction": 0.0,
            "earth_visible_fraction": 0.0,
            "both_fraction": 0.0,
            "longest_dark_hours": 0.0,
        }

    # Count how many time steps the Sun is strictly above the horizon (> 0 degrees)
    sunlit_steps = sum(1 for angle in sun_elevation_deg if angle > 0)

    # Count how many time steps the Earth is strictly above the horizon (> 0 degrees)
    earth_steps = sum(1 for angle in earth_elevation_deg if angle > 0)

    # Count how many time steps BOTH the Sun and Earth are visible at the same time
    both_steps = sum(
        1
        for sun_angle, earth_angle in zip(sun_elevation_deg, earth_elevation_deg)
        if sun_angle > 0 and earth_angle > 0
    )

    # Track the longest continuous streak where the Sun is at or below 0 degrees
    current_dark_steps = 0
    max_dark_steps = 0

    for angle in sun_elevation_deg:
        if angle <= 0:
            # Sun is below the horizon, so extend the current dark streak
            current_dark_steps += 1
            if current_dark_steps > max_dark_steps:
                max_dark_steps = current_dark_steps
        else:
            # Sun rose above 0 degrees, so reset the current dark streak
            current_dark_steps = 0

    # Convert the longest streak of steps into hours like 2 steps * 30 mins = 1.0 hour)
    longest_dark_hours = max_dark_steps * (step_minutes / 60.0)

    # Return all four metrics rounded to 4 decimal places for clean display
    return {
        "sunlit_fraction": round(sunlit_steps / total_steps, 4),
        "earth_visible_fraction": round(earth_steps / total_steps, 4),
        "both_fraction": round(both_steps / total_steps, 4),
        "longest_dark_hours": round(longest_dark_hours, 4),
    }
