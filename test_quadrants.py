
import numpy as np
import matplotlib.pyplot as plt
def second_quadrant_sin(theta, lut):
    normalized_theta = np.int32(PI - theta)
    index = (normalized_theta << lut_bits) >> (lut_bits -2)
    # index = term2
    index = min(index, len(lut) - 1)
    return lut[index]

def third_quadrant_sin(theta, lut):
    normalized_theta = np.int32(theta- PI)
    index = (normalized_theta << lut_bits) >> (lut_bits -2)
    index = min(index, len(lut) - 1)
    return -lut[index] + (1 << lut_bits)


def fourth_quadrant_sin(theta, lut):
    normalized_theta = np.int32(PI + PI - theta)
    index = (normalized_theta << lut_bits) >> (lut_bits -2)
    index = min(index, len(lut) - 1)  # Ensure index is within LUT bounds
    return -lut[index] + (1 << lut_bits)

lut_bits = 20
lut_size_quarter = 1 << lut_bits  # Number of points in the LUT
PI = lut_size_quarter >> 1
print(PI)
# Corrected LUT generation for the first quadrant (0 to π/2)
lut_gen_first_quadrant = [int((np.sin(np.pi / 2 * i / lut_size_quarter) + 1) * (2**(lut_bits - 1) - 1)) for i in range(lut_size_quarter)]
angles_first_quadrant = np.linspace(0, PI/2, lut_size_quarter)
# Sine values for the first quadrant from the LUT
sine_values_first_quadrant = [lut_gen_first_quadrant[int(i)] for i in np.linspace(0, lut_size_quarter - 1, lut_size_quarter)]

angles_second_quadrant = np.linspace(np.int32(PI/2), PI, lut_size_quarter)
# Sine values for the second quadrant using the symmetry
sine_values_second_quadrant = [second_quadrant_sin(theta, lut_gen_first_quadrant) for theta in angles_second_quadrant]
# Angles for the third quadrant (π/2 to π)
angles_third_quadrant = np.linspace(PI, np.int32((PI/2)*3), lut_size_quarter)
# Generate sine values for the third quadrant
sine_values_third_quadrant = [third_quadrant_sin(theta, lut_gen_first_quadrant) for theta in angles_third_quadrant]

# Angles for the fourth quadrant (3π/2 to 2π)
angles_fourth_quadrant = np.linspace(np.int32((PI/2)*3), 2 * PI, lut_size_quarter)

# Sine values for the fourth quadrant using the symmetry
sine_values_fourth_quadrant = [fourth_quadrant_sin(theta, lut_gen_first_quadrant) for theta in angles_fourth_quadrant]



plt.figure(figsize=(11, 6))

# Plot first quadrant
plt.plot(angles_first_quadrant, sine_values_first_quadrant, label='First Quadrant', marker='o')

# Plot second quadrant
plt.plot(angles_second_quadrant, sine_values_second_quadrant, label='Second Quadrant', marker='x')
plt.plot(angles_third_quadrant, sine_values_third_quadrant, label='Third Quadrant', marker='*')  # Third quadrant
plt.plot(angles_fourth_quadrant, sine_values_fourth_quadrant, label='4th Quadrant', marker='.')  # Third quadrant

plt.title('Sine Wave Values for First and Second Quadrants')
plt.xlabel('Angle (radians)')
plt.ylabel('Sine Value')
plt.grid(True)
plt.legend()
plt.show()
