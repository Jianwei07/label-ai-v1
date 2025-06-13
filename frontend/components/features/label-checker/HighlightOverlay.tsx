"use client";

import { useState, useEffect, useRef } from "react";
import { HighlightedElement } from "@/lib/types";

interface HighlightOverlayProps {
  highlights: HighlightedElement[];
  imageElementId: string;
  focusedHighlight: HighlightedElement | null; // This prop receives the hovered fault
}

export function HighlightOverlay({
  highlights,
  imageElementId,
  focusedHighlight,
}: HighlightOverlayProps) {
  const [imageDimensions, setImageDimensions] = useState({
    naturalWidth: 0,
    naturalHeight: 0,
    renderedWidth: 0,
    renderedHeight: 0,
  });
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const imageElement = document.getElementById(
      imageElementId
    ) as HTMLImageElement;

    const updateDimensions = () => {
      if (imageElement && imageElement.naturalWidth > 0) {
        setImageDimensions({
          naturalWidth: imageElement.naturalWidth,
          naturalHeight: imageElement.naturalHeight,
          renderedWidth: imageElement.offsetWidth,
          renderedHeight: imageElement.offsetHeight,
        });
      }
    };

    const handleLoad = () => {
      updateDimensions();
    };

    // If the image is already loaded/cached, update dimensions immediately
    if (imageElement && imageElement.complete) {
      handleLoad();
    }

    imageElement?.addEventListener("load", handleLoad);
    window.addEventListener("resize", updateDimensions);

    return () => {
      imageElement?.removeEventListener("load", handleLoad);
      window.removeEventListener("resize", updateDimensions);
    };
  }, [imageElementId, highlights]); // Rerun effect if image or highlights change

  const { naturalWidth, renderedWidth, renderedHeight } = imageDimensions;

  if (!naturalWidth || !highlights || highlights.length === 0) return null;

  // Calculate the scaling factor between the original image and the rendered image
  const scale = renderedWidth / naturalWidth;

  return (
    <div
      ref={overlayRef}
      className="absolute top-0 left-0 pointer-events-none" // Parent div should not capture pointer events
      style={{ width: `${renderedWidth}px`, height: `${renderedHeight}px` }}
    >
      {highlights.map((highlight, index) => {
        const { x, y, width, height } = highlight.bounding_box;

        // Scale the coordinates and dimensions
        const scaledBox = {
          left: x * scale,
          top: y * scale,
          width: width * scale,
          height: height * scale,
        };

        // --- FIX: Check if the current highlight is the one being focused ---
        const isFocused =
          focusedHighlight?.rule_id_ref === highlight.rule_id_ref;

        // --- FIX: Dynamic styling based on status and focus state ---
        const baseBorder = `border-2`;
        const colorBorder =
          highlight.status === "correct"
            ? "border-green-500"
            : "border-red-500";
        const focusBorder = isFocused ? "!border-4 !border-yellow-400" : ""; // Use ! to override hover

        const baseBg =
          highlight.status === "correct" ? "bg-green-500/20" : "bg-red-500/20";
        const focusBg = isFocused ? "!bg-yellow-400/30" : "";

        return (
          <div
            key={index}
            // --- FIX: Combined all dynamic classes ---
            className={`absolute group pointer-events-auto transition-all duration-150 ease-in-out hover:!bg-transparent ${baseBorder} ${colorBorder} ${focusBorder} ${baseBg} ${focusBg}`}
            style={{
              left: `${scaledBox.left}px`,
              top: `${scaledBox.top}px`,
              width: `${scaledBox.width}px`,
              height: `${scaledBox.height}px`,
            }}
          >
            {/* Tooltip that appears on hover OR when focused from the list */}
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
