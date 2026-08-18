import defaultImg from "./default.jpg"
import correctFirstTry from "./correct_first_try.jpg"
import correctStreak from "./correct_streak.jpeg"
import incorrect from "./incorrect.avif"
import repeatedMistake from "./repeated_mistake.png"
import giveUpRequest from "./give_up_request.webp"
import topicMastered from "./topic_mastered.png"
import frustration_warning from "./frustration_warning.webp"
import full_frustration from "./full_frustration.avif"
import comeback from "./comeback.jpg"
import difficulty_milestone from "./difficulty_milestone.jpg"

// New moods — drop matching image files into this folder and uncomment imports:
// import frustrationWarning from "./frustration_warning.png";
// import fullFrustration    from "./full_frustration.png";
// import comeback           from "./comeback.png";

export const sukunaMoods = {
  default:             defaultImg,
  correct_first_try:   correctFirstTry,
  correct_streak:      correctStreak,
  incorrect:           incorrect,
  repeated_mistake:    repeatedMistake,
  give_up_request:     giveUpRequest,
  topic_mastered:      topicMastered,

  // Swap nulls once you have images:
  frustration_warning:  frustration_warning,  // → frustrationWarning
  full_frustration:     full_frustration,  // → fullFrustration
  comeback:             comeback,  // → comeback
  difficulty_milestone: difficulty_milestone,  // → difficultyMilestone
};
