"""
Image preprocessing functions for curve extraction.
"""

import cv2
import numpy as np


def preprocess_image(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """
    Preprocess image for marker detection.

    Steps:
    1. Convert to grayscale
    2. Apply Gaussian blur
    3. Apply adaptive threshold

    Args:
        image: Input BGR image
        kernel_size: Kernel size for morphological operations

    Returns:
        Binary image (black background, white foreground)
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Apply adaptive threshold
    binary = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        2
    )

    return binary


def remove_lines(binary: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """
    Remove lines from binary image using morphological opening.

    This operation removes thin structures (lines) while preserving
    thicker structures (markers).

    Args:
        binary: Binary image
        kernel_size: Size of the morphological kernel

    Returns:
        Binary image with lines removed
    """
    # Create elliptical kernel for opening
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (kernel_size, kernel_size)
    )

    # Apply morphological opening
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return opened


def enhance_markers(binary: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """
    Enhance markers after line removal.

    Args:
        binary: Binary image with lines removed
        kernel_size: Size of the morphological kernel

    Returns:
        Enhanced binary image
    """
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (kernel_size, kernel_size)
    )

    # Close small gaps
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    return closed


def extract_color_mask(
    image: np.ndarray,
    target_color: tuple,
    tolerance: int = 15
) -> np.ndarray:
    """
    Extract pixels matching a target color using HSV color space.

    Args:
        image: Input BGR image
        target_color: Target BGR color tuple
        tolerance: HSV tolerance range (default ±15)

    Returns:
        Binary mask of matching pixels
    """
    # Convert to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Convert target color to HSV
    target_bgr = np.uint8([[target_color]])
    target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0]

    # Create HSV range with tolerance
    h, s, v = target_hsv
    lower = np.array([
        max(0, h - tolerance),
        max(0, s - 50),
        max(0, v - 50)
    ])
    upper = np.array([
        min(179, h + tolerance),
        min(255, s + 50),
        min(255, v + 50)
    ])

    # Handle hue wraparound for red colors
    if h < tolerance:
        # Red at lower end
        mask1 = cv2.inRange(hsv, np.array([0, lower[1], lower[2]]), upper)
        mask2 = cv2.inRange(
            hsv,
            np.array([179 - (tolerance - h), lower[1], lower[2]]),
            np.array([179, upper[1], upper[2]])
        )
        mask = cv2.bitwise_or(mask1, mask2)
    elif h > 179 - tolerance:
        # Red at upper end
        mask1 = cv2.inRange(hsv, lower, np.array([179, upper[1], upper[2]]))
        mask2 = cv2.inRange(
            hsv,
            np.array([0, lower[1], lower[2]]),
            np.array([tolerance - (179 - h), upper[1], upper[2]])
        )
        mask = cv2.bitwise_or(mask1, mask2)
    else:
        mask = cv2.inRange(hsv, lower, upper)

    return mask


def skeletonize(binary: np.ndarray) -> np.ndarray:
    """
    Extract skeleton from binary image using Zhang-Suen thinning.

    Args:
        binary: Binary image

    Returns:
        Skeleton image (1-pixel wide lines)
    """
    from skimage.morphology import skeletonize as sk_skeletonize

    # Ensure binary values are 0 and 1
    binary_normalized = (binary > 0).astype(np.uint8)

    # Apply skeletonization
    skeleton = sk_skeletonize(binary_normalized)

    return (skeleton * 255).astype(np.uint8)
