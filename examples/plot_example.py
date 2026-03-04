import matplotlib.pyplot as plt
import numpy as np
import graffiti_plot  # <-- Automatically supercharges all axes in the figure!

# Enable the global footer
graffiti_plot.set_footer(True, prefix="Fiber Optics Simulation | ")

# Create a figure with 2 subplots (stacked vertically)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# ==========================================
# Generate Sample Data
# ==========================================
# Time array: 0 to 10 nanoseconds
t = np.linspace(0, 10e-9, 1000) 

# Signal 1: Clean Input Pulse (5 mW peak at 3 ns)
input_pulse = np.exp(-((t - 3e-9) / 0.5e-9)**2) * 5e-3 

# Signal 2: Dispersed/Attenuated Output Pulse + Noise
noise = np.random.normal(0, 1.5e-4, len(t))
output_pulse = np.exp(-((t - 6e-9) / 1.2e-9)**2) * 1.5e-3 + noise

# ==========================================
# Subplot 1: Transmitter (Top)
# ==========================================
ax1.plot(t, input_pulse, label="Input Pulse (Clean)", color='dodgerblue', linewidth=2)
ax1.set_title("Transmitter Signal")
ax1.set_ylabel("Optical Power")
ax1.legend()
ax1.set_si_units(x='s', y='W') # Automatically scales to ns and mW!

# ==========================================
# Subplot 2: Receiver (Bottom)
# ==========================================
ax2.plot(t, output_pulse, label="Output Pulse (Dispersed)", color='darkorange', linewidth=2)
ax2.set_title("Received Signal (After 50km Fiber)")
ax2.set_xlabel("Time")
ax2.set_ylabel("Optical Power")
ax2.legend()
ax2.set_si_units(x='s', y='W')

# Adjust layout so titles and labels don't overlap
plt.tight_layout()

# Show the interactive plot!
# PRO TIP: Press 'X' on your keyboard to link the axes, then zoom in!
plt.show()