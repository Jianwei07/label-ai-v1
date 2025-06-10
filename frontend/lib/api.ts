import axios from "axios";
import { LabelAnalysisResult } from "./types";

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

/**
 * Submits a label image and its rules file for analysis.
 *
 * @param imageFile The image file to be analyzed.
 * @param rulesFile The rules document file (.docx, .json, .yaml).
 * @param sensitivity The sensitivity level (0-100).
 * @returns The full analysis result from the backend.
 */
export const submitLabelForAnalysis = async (
  imageFile: File,
  rulesFile: File, // Changed from RuleSet to File
  sensitivity: number = 50
): Promise<LabelAnalysisResult> => {
  // Use FormData to send both files and other data fields
  const formData = new FormData();
  formData.append("label_image", imageFile);
  formData.append("rules_file", rulesFile); // Send the rules file
  formData.append("sensitivity", sensitivity.toString());

  try {
    const response = await apiClient.post<LabelAnalysisResult>(
      "/labels/check",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const errorDetail = error.response.data.detail;
      if (typeof errorDetail === "string") {
        throw new Error(errorDetail);
      } else if (Array.isArray(errorDetail) && errorDetail[0]?.msg) {
        throw new Error(
          `Validation Error: ${errorDetail[0].loc.join(".")} - ${
            errorDetail[0].msg
          }`
        );
      }
      throw new Error(
        error.response.data.message || "An unknown API error occurred."
      );
    }
    throw new Error("An unexpected network error occurred.");
  }
};
