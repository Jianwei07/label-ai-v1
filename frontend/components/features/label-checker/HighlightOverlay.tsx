"use client";

import { useState, useEffect, useRef } from "react";
import { HighlightedElement } from "@/lib/types";

interface HighlightOverlayProps {
  highlights: HighlightedElement[];
  imageElementId: string;
  focusedHighlight: HighlightedElement | null;
}

export function HighlightOverlay({
  highlights,
  imageElementId,
  focusedHighlight,
}: HighlightOverlayProps) {
  const [imageRenderState, setImageRenderState] = useState({
    scale: 0,
    offsetX: 0,
    offsetY: 0,
    containerWidth: 0,
    containerHeight: 0,
  });
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const imageElement = document.getElementById(
      imageElementId
    ) as HTMLImageElement;

    const updateDimensions = () => {
      if (
        imageElement &&
        imageElement.naturalWidth > 0 &&
        imageElement.parentElement
      ) {
        const { naturalWidth, naturalHeight } = imageElement;
        // Get the dimensions of the container that the image is trying to fit into
        const { width: containerWidth, height: containerHeight } =
          imageElement.parentElement.getBoundingClientRect();

        // Determine the scale based on which dimension is the limiting factor
        const scale = Math.min(
          containerWidth / naturalWidth,
          containerHeight / naturalHeight
        );

        // Calculate the final rendered size of the image inside the container
        const renderedWidth = naturalWidth * scale;
        const renderedHeight = naturalHeight * scale;

        // Calculate the empty space (letterboxing) on each side
        const offsetX = (containerWidth - renderedWidth) / 2;
        const offsetY = (containerHeight - renderedHeight) / 2;

        setImageRenderState({
          scale,
          offsetX,
          offsetY,
          containerWidth,
          containerHeight,
        });
      }
    };

    // If the image is already loaded/cached, update dimensions immediately
    if (imageElement && imageElement.complete) {
      updateDimensions();
    }

    // Add event listeners to handle image loading and window resizing
    imageElement?.addEventListener("load", updateDimensions);
    window.addEventListener("resize", updateDimensions);

    // Also run when highlights appear, as the image might have loaded by then
    updateDimensions();

    // Cleanup function to remove listeners
    return () => {
      imageElement?.removeEventListener("load", updateDimensions);
      window.removeEventListener("resize", updateDimensions);
    };
  }, [imageElementId, highlights]); // Rerun effect when highlights appear

  const { scale, offsetX, offsetY, containerWidth, containerHeight } =
    imageRenderState;

  // Do not render anything until the scale has been calculated
  if (scale === 0 || !highlights || highlights.length === 0) return null;

  return (
    <div
      ref={overlayRef}
      className="absolute top-0 left-0 pointer-events-none"
      style={{ width: `${containerWidth}px`, height: `${containerHeight}px` }}
    >
      {highlights.map((highlight, index) => {
        const { x, y, width, height } = highlight.bounding_box;

        const isFocused =
          focusedHighlight?.rule_id_ref === highlight.rule_id_ref;

        // Apply the scale AND the calculated offset for precise positioning
        const scaledBox = {
          left: x * scale + offsetX,
          top: y * scale + offsetY,
          width: width * scale,
          height: height * scale,
        };

        const baseBorder = `border-2`;
        const colorBorder =
          highlight.status === "correct"
            ? "border-green-500"
            : "border-red-500";
        const focusBorder = isFocused ? "!border-4 !border-yellow-400" : "";

        const baseBg =
          highlight.status === "correct" ? "bg-green-500/20" : "bg-red-500/20";
        const focusBg = isFocused ? "!bg-yellow-400/30" : "";

        return (
          <div
            key={index}
            className={`absolute group pointer-events-auto transition-all duration-150 ease-in-out hover:!bg-transparent ${baseBorder} ${colorBorder} ${focusBorder} ${baseBg} ${focusBg}`}
            style={{
              left: `${scaledBox.left}px`,
              top: `${scaledBox.top}px`,
              width: `${scaledBox.width}px`,
              height: `${scaledBox.height}px`,
            }}
          >
            {/* Tooltip */}
            <div
              className={`absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs p-2 text-xs text-white bg-gray-900/80 dark:bg-gray-900 rounded-md shadow-lg transition-opacity pointer-events-none z-10 ${
                isFocused ? "opacity-100" : "opacity-0 group-hover:opacity-100"
              }`}
            >
              <p className="font-bold">{highlight.status.toUpperCase()}</p>
              <p>{highlight.message}</p>
              {highlight.found_value && (
                <p>
                  <strong>Found:</strong> {highlight.found_value}
                </p>
              )}
              {highlight.expected_value && (
                <p>
                  <strong>Expected:</strong> {highlight.expected_value}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
