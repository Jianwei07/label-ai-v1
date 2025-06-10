"use client";

import { useState, useEffect, useRef } from "react";
import { HighlightedElement } from "@/lib/types";

interface HighlightOverlayProps {
  highlights: HighlightedElement[];
  imageElementId: string; // The ID of the <img> element
}

export function HighlightOverlay({
  highlights,
  imageElementId,
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
      className="absolute top-0 left-0"
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

        const borderColor =
          highlight.status === "correct"
            ? "border-green-500"
            : "border-red-500";
        const bgColor =
          highlight.status === "correct" ? "bg-green-500/20" : "bg-red-500/20";

        return (
          <div
            key={index}
            className={`absolute border-2 ${borderColor} ${bgColor} group pointer-events-auto transition-all duration-150 hover:!bg-transparent`}
            style={{
              left: `${scaledBox.left}px`,
              top: `${scaledBox.top}px`,
              width: `${scaledBox.width}px`,
              height: `${scaledBox.height}px`,
            }}
          >
            {/* Tooltip that appears on hover */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs p-2 text-xs text-white bg-gray-900/80 dark:bg-gray-900 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
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
