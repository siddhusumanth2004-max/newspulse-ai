import React, {
  useEffect,
  useMemo,
  useState
} from "react";

import axios from "axios";

import "./NewsPulseExperienceHub.css";


const HISTORY_KEY =
  "newspulse_intelligence_history_v1";

const MAX_HISTORY = 20;


// =====================================================
// HELPERS
// =====================================================

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}


function normalizeRole(value) {
  const role = String(value || "").toLowerCase();

  if (role.includes("student")) return "student";
  if (role.includes("developer")) return "developer";
  if (role.includes("research")) return "researcher";
  if (role.includes("business")) return "business";

  return "general";
}


function roleLabel(value) {
  const role = normalizeRole(value);

  if (role === "student") return "Student";
  if (role === "developer") return "Developer";
  if (role === "researcher") return "Researcher";
  if (role === "business") return "Business Owner";

  return "General Reader";
}


function loadHistory() {
  try {
    const raw =
      localStorage.getItem(HISTORY_KEY);

    if (!raw) {
      return [];
    }

    const parsed =
      JSON.parse(raw);

    return Array.isArray(parsed)
      ? parsed
      : [];
  }

  catch (error) {
    console.log(
      "NewsPulse history load skipped.",
      error
    );

    return [];
  }
}


function saveHistory(history) {
  try {
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify(history)
    );
  }

  catch (error) {
    console.log(
      "NewsPulse history save skipped.",
      error
    );
  }
}


function formatDate(value) {
  if (!value) {
    return "Unknown time";
  }

  try {
    return new Date(value).toLocaleString();
  }

  catch {
    return String(value);
  }
}


function extractPayload(response) {
  let payload =
    response?.data;

  if (
    payload?.data &&
    Array.isArray(payload.data.stories)
  ) {
    payload = payload.data;
  }

  else if (
    payload?.result &&
    Array.isArray(payload.result.stories)
  ) {
    payload = payload.result;
  }

  return payload;
}


// =====================================================
// KEEP ONLY USEFUL HISTORY DATA
// =====================================================

function compactStory(story) {
  return {
    cluster_id:
      story?.cluster_id || null,

    representative_title:
      story?.representative_title || "",

    article_count:
      story?.article_count || 0,

    living_story_id:
      story?.living_story_id || null,

    memory_action:
      story?.memory_action || "CREATED",

    memory_similarity:
      story?.memory_similarity || 0,

    briefing:
      story?.briefing || {},

    evidence:
      story?.evidence || null,

    evidence_note:
      story?.evidence_note || "",

    impact:
      story?.impact || null,

    delta:
      story?.delta || null,

    sources:
      safeArray(story?.sources).slice(0, 5)
  };
}


function createHistoryEntry(payload) {
  return {
    id:
      `${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 8)}`,

    generated_at:
      new Date().toISOString(),

    user_role:
      payload?.user_role ||
      "General Reader",

    agent_name:
      payload?.agent_name ||
      "NewsPulse AI",

    stories:
      safeArray(
        payload?.stories
      ).map(compactStory)
  };
}


// =====================================================
// STORY MATCHING FOR REPLAY
// =====================================================

function sameStory(first, second) {
  if (!first || !second) {
    return false;
  }

  if (
    first.living_story_id &&
    second.living_story_id
  ) {
    return (
      first.living_story_id ===
      second.living_story_id
    );
  }

  const firstHeadline =
    String(
      first?.briefing?.headline ||
      first?.representative_title ||
      ""
    )
      .trim()
      .toLowerCase();

  const secondHeadline =
    String(
      second?.briefing?.headline ||
      second?.representative_title ||
      ""
    )
      .trim()
      .toLowerCase();

  return (
    firstHeadline &&
    firstHeadline === secondHeadline
  );
}


// =====================================================
// ASK THIS STORY
// INSTANT ANSWERS FROM EXISTING INTELLIGENCE
// =====================================================

function answerStoryQuestion(
  story,
  question
) {
  if (!story) {
    return "Generate or reopen a briefing first.";
  }

  const q =
    String(question || "")
      .trim()
      .toLowerCase();

  const briefing =
    story.briefing || {};

  const impact =
    story.impact || {};

  const evidence =
    story.evidence || {};

  const delta =
    story.delta || {};


  if (
    q.includes("simple") ||
    q.includes("summary") ||
    q.includes("explain")
  ) {
    return (
      briefing.summary ||
      briefing.what_happened ||
      "No summary is available."
    );
  }


  if (
    q.includes("what happened") ||
    q.includes("happened")
  ) {
    return (
      briefing.what_happened ||
      briefing.summary ||
      "No event explanation is available."
    );
  }


  if (
    q.includes("why") ||
    q.includes("matter")
  ) {
    return (
      briefing.why_it_matters ||
      impact.why_it_matters ||
      "NewsPulse did not return a why-it-matters explanation."
    );
  }


  if (
    q.includes("impact") ||
    q.includes("affect")
  ) {
    const parts = [];

    if (impact.user_specific_impact) {
      parts.push(
        `For you: ${impact.user_specific_impact}`
      );
    }

    if (impact.direct_impact) {
      parts.push(
        `Direct impact: ${impact.direct_impact}`
      );
    }

    if (impact.indirect_impact) {
      parts.push(
        `Indirect impact: ${impact.indirect_impact}`
      );
    }

    if (impact.impact_level) {
      parts.push(
        `Impact level: ${impact.impact_level}`
      );
    }

    return (
      parts.join("\n\n") ||
      "No impact analysis is available."
    );
  }


  if (
    q.includes("change") ||
    q.includes("new")
  ) {
    const changed =
      safeArray(
        delta.changed_information
      );

    const fresh =
      safeArray(
        delta.new_information
      );

    const lines = [];

    if (delta.what_changed) {
      lines.push(delta.what_changed);
    }

    fresh.forEach(
      item =>
        lines.push(`+ ${item}`)
    );

    changed.forEach(
      item =>
        lines.push(`~ ${item}`)
    );

    return (
      lines.join("\n") ||
      "No major change was recorded for this story."
    );
  }


  if (
    q.includes("uncertain") ||
    q.includes("unknown")
  ) {
    const uncertain =
      safeArray(
        delta.still_uncertain
      );

    if (!uncertain.length) {
      return (
        "NewsPulse did not identify any major unresolved points."
      );
    }

    return uncertain
      .map(
        item => `? ${item}`
      )
      .join("\n");
  }


  if (
    q.includes("fact")
  ) {
    const facts =
      safeArray(
        briefing.key_facts
      );

    if (!facts.length) {
      return "No key facts are available.";
    }

    return facts
      .map(
        item => `• ${item}`
      )
      .join("\n");
  }


  if (
    q.includes("evidence") ||
    q.includes("source") ||
    q.includes("agree") ||
    q.includes("contradict")
  ) {
    const parts = [];

    if (evidence.evidence_summary) {
      parts.push(
        evidence.evidence_summary
      );
    }

    const supporting =
      safeArray(
        evidence.supporting_sources
      );

    const contradicting =
      safeArray(
        evidence.contradicting_sources
      );

    if (supporting.length) {
      parts.push(
        `Supporting sources:\n${supporting
          .map(item => `✓ ${item}`)
          .join("\n")}`
      );
    }

    if (contradicting.length) {
      parts.push(
        `Contradicting sources:\n${contradicting
          .map(item => `! ${item}`)
          .join("\n")}`
      );
    }

    return (
      parts.join("\n\n") ||
      "No multi-source evidence details are available."
    );
  }


  return (
    `${briefing.summary || briefing.what_happened || ""}\n\n` +
    `${briefing.why_it_matters || ""}\n\n` +
    "Try asking: What changed? Why does this matter? What is uncertain? What is the impact? Compare the sources."
  ).trim();
}


// =====================================================
// MAIN COMPONENT
// =====================================================

function NewsPulseExperienceHub() {

  const [
    history,
    setHistory
  ] = useState(
    () => loadHistory()
  );


  const [
    currentEntry,
    setCurrentEntry
  ] = useState(
    () => loadHistory()[0] || null
  );


  const [
    selectedStoryIndex,
    setSelectedStoryIndex
  ] = useState(0);


  const [
    isOpen,
    setIsOpen
  ] = useState(false);


  const [
    mode,
    setMode
  ] = useState("history");


  const [
    historyFilter,
    setHistoryFilter
  ] = useState("all");


  const [
    question,
    setQuestion
  ] = useState("");


  const [
    answer,
    setAnswer
  ] = useState("");


  const [
    replayStep,
    setReplayStep
  ] = useState(0);


  const [
    replayPlaying,
    setReplayPlaying
  ] = useState(false);


  // ===================================================
  // CAPTURE SUCCESSFUL BRIEFINGS
  // ===================================================

  useEffect(
    () => {

      const interceptor =
        axios.interceptors.response.use(

          response => {

            try {
              const url =
                String(
                  response
                    ?.config
                    ?.url || ""
                );

              if (
                !url.includes(
                  "/api/orchestrate"
                )
              ) {
                return response;
              }

              const payload =
                extractPayload(
                  response
                );

              if (
                !payload ||
                !Array.isArray(
                  payload.stories
                )
              ) {
                return response;
              }

              const entry =
                createHistoryEntry(
                  payload
                );


              setHistory(
                previous => {

                  const firstHeadline =
                    entry
                      ?.stories?.[0]
                      ?.briefing
                      ?.headline || "";

                  const now =
                    Date.now();

                  const duplicate =
                    previous.some(
                      item => {

                        const itemHeadline =
                          item
                            ?.stories?.[0]
                            ?.briefing
                            ?.headline || "";

                        const age =
                          Math.abs(
                            now -
                            new Date(
                              item.generated_at
                            ).getTime()
                          );

                        return (
                          itemHeadline ===
                            firstHeadline &&
                          age < 3000
                        );
                      }
                    );


                  if (duplicate) {
                    return previous;
                  }


                  const updated = [
                    entry,
                    ...previous
                  ].slice(
                    0,
                    MAX_HISTORY
                  );


                  saveHistory(
                    updated
                  );


                  return updated;
                }
              );


              setCurrentEntry(
                entry
              );

              setSelectedStoryIndex(
                0
              );

            }

            catch (error) {
              console.log(
                "NewsPulse history capture skipped.",
                error
              );
            }

            return response;
          },

          error =>
            Promise.reject(error)

        );


      return () => {
        axios
          .interceptors
          .response
          .eject(
            interceptor
          );
      };

    },
    []
  );


  // ===================================================
  // CURRENT STORY
  // ===================================================

  const stories =
    safeArray(
      currentEntry?.stories
    );


  const currentStory =
    stories[
      selectedStoryIndex
    ] || null;


  useEffect(
    () => {

      if (
        selectedStoryIndex >=
        stories.length
      ) {
        setSelectedStoryIndex(0);
      }

    },
    [
      selectedStoryIndex,
      stories.length
    ]
  );


  // ===================================================
  // FILTERED HISTORY
  // ===================================================

  const filteredHistory =
    useMemo(
      () => {

        if (
          historyFilter === "all"
        ) {
          return history;
        }

        return history.filter(
          entry =>
            normalizeRole(
              entry.user_role
            ) ===
            historyFilter
        );

      },
      [
        history,
        historyFilter
      ]
    );


  // ===================================================
  // STORY REPLAY EVENTS
  // ===================================================

  const replayEvents =
    useMemo(
      () => {

        if (!currentStory) {
          return [];
        }

        const events = [];


        [...history]
          .reverse()
          .forEach(
            entry => {

              const matching =
                safeArray(
                  entry.stories
                ).find(
                  story =>
                    sameStory(
                      currentStory,
                      story
                    )
                );


              if (!matching) {
                return;
              }


              events.push({
                id:
                  `${entry.id}-${matching.living_story_id || "story"}`,

                time:
                  entry.generated_at,

                action:
                  matching.memory_action ||
                  "ANALYZED",

                headline:
                  matching?.briefing?.headline ||
                  matching.representative_title ||
                  "NewsPulse Story",

                change:
                  matching?.delta?.what_changed ||
                  matching?.briefing?.what_happened ||
                  matching?.briefing?.summary ||
                  "Story intelligence generated."
              });
            }
          );


        if (
          events.length <= 1
        ) {
          const delta =
            currentStory.delta || {};

          const extra = [
            ...safeArray(
              delta.new_information
            ).map(
              value => ({
                action: "NEW",
                change: value
              })
            ),

            ...safeArray(
              delta.confirmed_information
            ).map(
              value => ({
                action: "CONFIRMED",
                change: value
              })
            ),

            ...safeArray(
              delta.changed_information
            ).map(
              value => ({
                action: "CHANGED",
                change: value
              })
            ),

            ...safeArray(
              delta.corrected_information
            ).map(
              value => ({
                action: "CORRECTED",
                change: value
              })
            )
          ];


          extra
            .slice(0, 5)
            .forEach(
              (event, index) => {

                events.push({
                  id:
                    `synthetic-${index}`,

                  time:
                    currentEntry
                      ?.generated_at,

                  action:
                    event.action,

                  headline:
                    currentStory
                      ?.briefing
                      ?.headline ||
                    "Story Update",

                  change:
                    event.change
                });

              }
            );
        }


        return events;

      },
      [
        currentStory,
        currentEntry,
        history
      ]
    );


  // ===================================================
  // REPLAY ANIMATION
  // ===================================================

  useEffect(
    () => {

      if (!replayPlaying) {
        return undefined;
      }


      if (!replayEvents.length) {
        setReplayPlaying(false);

        return undefined;
      }


      const timer =
        setInterval(
          () => {

            setReplayStep(
              previous => {

                if (
                  previous >=
                  replayEvents.length - 1
                ) {
                  setReplayPlaying(false);

                  return previous;
                }

                return previous + 1;
              }
            );

          },
          850
        );


      return () =>
        clearInterval(timer);

    },
    [
      replayPlaying,
      replayEvents.length
    ]
  );


  // ===================================================
  // RADAR DATA
  // ===================================================

  const radarStats =
    useMemo(
      () => {

        const counts = {};


        history.forEach(
          entry => {

            safeArray(
              entry.stories
            ).forEach(
              story => {

                const category =
                  String(
                    story
                      ?.briefing
                      ?.category ||
                    "General"
                  )
                    .trim();

                counts[category] =
                  (
                    counts[category] ||
                    0
                  ) + 1;
              }
            );

          }
        );


        return Object
          .entries(counts)
          .map(
            ([name, count]) => ({
              name,
              count
            })
          )
          .sort(
            (a, b) =>
              b.count -
              a.count
          )
          .slice(0, 8);

      },
      [history]
    );


  const radarMaximum =
    radarStats.length
      ? Math.max(
          ...radarStats.map(
            item => item.count
          )
        )
      : 1;


  // ===================================================
  // OPEN HISTORICAL BRIEFING
  // ===================================================

  function openHistoryEntry(entry) {
    setCurrentEntry(entry);

    setSelectedStoryIndex(0);

    setAnswer("");

    setQuestion("");

    setMode("ask");
  }


  // ===================================================
  // ASK
  // ===================================================

  function askStory(
    customQuestion
  ) {
    const finalQuestion =
      String(
        customQuestion ??
        question
      ).trim();


    if (!finalQuestion) {
      return;
    }


    setQuestion(
      finalQuestion
    );


    setAnswer(
      answerStoryQuestion(
        currentStory,
        finalQuestion
      )
    );
  }


  // ===================================================
  // PLAY REPLAY
  // ===================================================

  function startReplay() {
    setReplayStep(0);

    setReplayPlaying(true);
  }


  // ===================================================
  // CLEAR HISTORY
  // ===================================================

  function clearHistory() {
    localStorage.removeItem(
      HISTORY_KEY
    );

    setHistory([]);

    setCurrentEntry(null);

    setSelectedStoryIndex(0);

    setReplayStep(0);

    setReplayPlaying(false);
  }


  // ===================================================
  // RENDER
  // ===================================================

  return (

    <>

      {/* =================================================
          FLOATING HUB BUTTON
          ================================================= */}

      <button
        type="button"
        className="np-hub-launcher"
        onClick={
          () => setIsOpen(true)
        }
      >

        <span className="np-hub-core">
          NP
        </span>

        <span className="np-hub-launcher-copy">

          INTELLIGENCE

          <strong>
            HUB
          </strong>

        </span>

      </button>


      {/* =================================================
          BACKDROP
          ================================================= */}

      <div
        className={
          isOpen
            ? "np-hub-backdrop active"
            : "np-hub-backdrop"
        }
        onClick={
          () => setIsOpen(false)
        }
      ></div>


      {/* =================================================
          DRAWER
          ================================================= */}

      <aside
        className={
          isOpen
            ? "np-hub-drawer active"
            : "np-hub-drawer"
        }
      >


        {/* HEADER */}

        <div className="np-hub-header">

          <div>

            <span>
              NEWSPULSE ROYAL SYSTEM
            </span>

            <h2>
              Intelligence Hub
            </h2>

          </div>


          <button
            type="button"
            onClick={
              () => setIsOpen(false)
            }
          >
            ×
          </button>

        </div>


        {/* =================================================
            NAVIGATION
            ================================================= */}

        <div className="np-hub-tabs">

          <button
            className={
              mode === "history"
                ? "active"
                : ""
            }
            onClick={
              () => setMode("history")
            }
          >
            HISTORY
          </button>


          <button
            className={
              mode === "replay"
                ? "active"
                : ""
            }
            onClick={
              () => setMode("replay")
            }
          >
            REPLAY
          </button>


          <button
            className={
              mode === "ask"
                ? "active"
                : ""
            }
            onClick={
              () => setMode("ask")
            }
          >
            ASK
          </button>


          <button
            className={
              mode === "radar"
                ? "active"
                : ""
            }
            onClick={
              () => setMode("radar")
            }
          >
            RADAR
          </button>

        </div>


        {/* =================================================
            STORY SWITCHER
            ================================================= */}

        {
          stories.length > 1 &&
          mode !== "history" &&
          mode !== "radar" &&
          (

            <div className="np-hub-story-tabs">

              {
                stories.map(
                  (story, index) => (

                    <button
                      key={
                        story.living_story_id ||
                        index
                      }
                      className={
                        selectedStoryIndex ===
                        index
                          ? "active"
                          : ""
                      }
                      onClick={
                        () =>
                          setSelectedStoryIndex(
                            index
                          )
                      }
                    >

                      {
                        String(
                          index + 1
                        ).padStart(
                          2,
                          "0"
                        )
                      }

                    </button>

                  )
                )
              }

            </div>

          )
        }


        <div className="np-hub-scroll">


          {/* =================================================
              HISTORY
              ================================================= */}

          {
            mode === "history" &&
            (

              <section className="np-hub-page">

                <div className="np-hub-page-heading">

                  <div>

                    <span>
                      INTELLIGENCE ARCHIVE
                    </span>

                    <h3>
                      Briefing History
                    </h3>

                  </div>


                  {
                    history.length > 0 &&
                    (

                      <button
                        className="np-clear-history"
                        onClick={
                          clearHistory
                        }
                      >
                        CLEAR
                      </button>

                    )
                  }

                </div>


                <div className="np-history-filters">

                  {
                    [
                      ["all", "ALL"],
                      ["student", "STUDENT"],
                      ["developer", "DEV"],
                      ["researcher", "R&D"],
                      ["business", "BUSINESS"],
                      ["general", "GENERAL"]
                    ].map(
                      ([value, label]) => (

                        <button
                          key={value}
                          className={
                            historyFilter ===
                            value
                              ? "active"
                              : ""
                          }
                          onClick={
                            () =>
                              setHistoryFilter(
                                value
                              )
                          }
                        >
                          {label}
                        </button>

                      )
                    )
                  }

                </div>


                {
                  filteredHistory.length ===
                  0
                    ? (

                      <div className="np-hub-empty">

                        <strong>
                          No Intelligence History
                        </strong>

                        <p>
                          Generate a briefing and
                          NewsPulse will automatically
                          save it here.
                        </p>

                      </div>

                    )
                    : (

                      <div className="np-history-list">

                        {
                          filteredHistory.map(
                            entry => {

                              const first =
                                entry
                                  ?.stories?.[0];

                              const role =
                                normalizeRole(
                                  entry.user_role
                                );

                              return (

                                <article
                                  className="np-history-card"
                                  key={entry.id}
                                >

                                  <div className="np-history-top">

                                    <span
                                      className={
                                        `np-role-chip ${role}`
                                      }
                                    >
                                      {
                                        roleLabel(
                                          entry.user_role
                                        )
                                      }
                                    </span>

                                    <small>
                                      {
                                        formatDate(
                                          entry.generated_at
                                        )
                                      }
                                    </small>

                                  </div>


                                  <h4>
                                    {
                                      first
                                        ?.briefing
                                        ?.headline ||
                                      "NewsPulse Briefing"
                                    }
                                  </h4>


                                  <p>
                                    {
                                      first
                                        ?.briefing
                                        ?.summary ||
                                      "Saved NewsPulse intelligence briefing."
                                    }
                                  </p>


                                  <div className="np-history-footer">

                                    <span>
                                      {
                                        entry
                                          .stories
                                          .length
                                      }
                                      {" "}
                                      STORIES
                                    </span>


                                    <button
                                      onClick={
                                        () =>
                                          openHistoryEntry(
                                            entry
                                          )
                                      }
                                    >
                                      REOPEN →
                                    </button>

                                  </div>

                                </article>

                              );
                            }
                          )
                        }

                      </div>

                    )
                }

              </section>

            )
          }


          {/* =================================================
              STORY EVOLUTION REPLAY
              ================================================= */}

          {
            mode === "replay" &&
            (

              <section className="np-hub-page">

                <div className="np-hub-page-heading">

                  <div>

                    <span>
                      LIVING STORY MEMORY
                    </span>

                    <h3>
                      Story Evolution Replay
                    </h3>

                  </div>


                  {
                    replayEvents.length > 0 &&
                    (

                      <button
                        className="np-replay-button"
                        onClick={
                          startReplay
                        }
                      >

                        {
                          replayPlaying
                            ? "PLAYING..."
                            : "▶ REPLAY"
                        }

                      </button>

                    )
                  }

                </div>


                {
                  !currentStory
                    ? (

                      <div className="np-hub-empty">

                        <strong>
                          No Story Selected
                        </strong>

                        <p>
                          Generate or reopen a briefing
                          first.
                        </p>

                      </div>

                    )
                    : (

                      <>

                        <div className="np-replay-headline">

                          <span>
                            CURRENT STORY
                          </span>

                          <h4>
                            {
                              currentStory
                                ?.briefing
                                ?.headline ||
                              currentStory
                                ?.representative_title
                            }
                          </h4>

                        </div>


                        <div className="np-replay-timeline">

                          {
                            replayEvents.map(
                              (
                                event,
                                index
                              ) => (

                                <div
                                  key={event.id}
                                  className={
                                    index <= replayStep
                                      ? "np-replay-event active"
                                      : "np-replay-event"
                                  }
                                >

                                  <div className="np-replay-node">

                                    {
                                      index ===
                                      replayEvents.length - 1
                                        ? "◆"
                                        : "●"
                                    }

                                  </div>


                                  <div className="np-replay-content">

                                    <div className="np-replay-meta">

                                      <span>
                                        {event.action}
                                      </span>

                                      <small>
                                        {
                                          formatDate(
                                            event.time
                                          )
                                        }
                                      </small>

                                    </div>


                                    <h5>
                                      {
                                        event.headline
                                      }
                                    </h5>


                                    <p>
                                      {
                                        event.change
                                      }
                                    </p>

                                  </div>

                                </div>

                              )
                            )
                          }

                        </div>

                      </>

                    )
                }

              </section>

            )
          }


          {/* =================================================
              ASK THIS STORY
              ================================================= */}

          {
            mode === "ask" &&
            (

              <section className="np-hub-page">

                <div className="np-hub-page-heading">

                  <div>

                    <span>
                      INSTANT STORY INTELLIGENCE
                    </span>

                    <h3>
                      Ask This Story
                    </h3>

                  </div>

                </div>


                {
                  !currentStory
                    ? (

                      <div className="np-hub-empty">

                        <strong>
                          No Story Available
                        </strong>

                        <p>
                          Generate a briefing first or
                          reopen one from History.
                        </p>

                      </div>

                    )
                    : (

                      <>

                        <div className="np-ask-story">

                          <span>
                            ACTIVE STORY
                          </span>

                          <h4>
                            {
                              currentStory
                                ?.briefing
                                ?.headline ||
                              currentStory
                                ?.representative_title
                            }
                          </h4>

                        </div>


                        <div className="np-quick-prompts">

                          {
                            [
                              "Explain this simply",
                              "What changed?",
                              "Why does this matter?",
                              "What is the impact?",
                              "What is still uncertain?",
                              "Compare the sources",
                              "Give me the key facts"
                            ].map(
                              prompt => (

                                <button
                                  key={prompt}
                                  onClick={
                                    () =>
                                      askStory(
                                        prompt
                                      )
                                  }
                                >
                                  {prompt}
                                </button>

                              )
                            )
                          }

                        </div>


                        <form
                          className="np-ask-box"
                          onSubmit={
                            event => {

                              event.preventDefault();

                              askStory();

                            }
                          }
                        >

                          <input
                            value={question}
                            onChange={
                              event =>
                                setQuestion(
                                  event.target.value
                                )
                            }
                            placeholder="Ask NewsPulse about this story..."
                          />

                          <button type="submit">
                            ASK
                          </button>

                        </form>


                        {
                          answer &&
                          (

                            <div className="np-answer-card">

                              <div className="np-answer-header">

                                <span className="np-answer-core">
                                  NP
                                </span>

                                <div>

                                  <strong>
                                    NewsPulse Answer
                                  </strong>

                                  <small>
                                    INSTANT • CURRENT
                                    BRIEFING INTELLIGENCE
                                  </small>

                                </div>

                              </div>


                              <p>
                                {answer}
                              </p>

                            </div>

                          )
                        }

                      </>

                    )
                }


                <div className="np-zero-ai-note">

                  This instant mode reuses the existing
                  briefing, evidence, impact and delta.
                  It does not create another Claude
                  request.

                </div>

              </section>

            )
          }


          {/* =================================================
              NEWSPULSE RADAR
              ================================================= */}

          {
            mode === "radar" &&
            (

              <section className="np-hub-page">

                <div className="np-hub-page-heading">

                  <div>

                    <span>
                      INTELLIGENCE ACTIVITY
                    </span>

                    <h3>
                      NewsPulse Radar
                    </h3>

                  </div>

                </div>


                {
                  radarStats.length === 0
                    ? (

                      <div className="np-hub-empty">

                        <strong>
                          Radar Is Waiting
                        </strong>

                        <p>
                          Generate briefings to build
                          your NewsPulse intelligence
                          radar.
                        </p>

                      </div>

                    )
                    : (

                      <>

                        <div className="np-radar-system">


                          <div className="np-radar-ring ring-1"></div>

                          <div className="np-radar-ring ring-2"></div>

                          <div className="np-radar-ring ring-3"></div>


                          <div className="np-radar-scan"></div>


                          <div className="np-radar-core">
                            NP
                          </div>


                          {
                            radarStats
                              .slice(0, 6)
                              .map(
                                (
                                  item,
                                  index
                                ) => {

                                  const angle =
                                    (
                                      360 /
                                      Math.min(
                                        radarStats.length,
                                        6
                                      )
                                    ) * index;

                                  return (

                                    <div
                                      key={item.name}
                                      className="np-radar-node"
                                      style={{
                                        transform:
                                          `translate(-50%, -50%) rotate(${angle}deg) translateY(-112px) rotate(${-angle}deg)`
                                      }}
                                    >

                                      <strong>
                                        {
                                          item.name
                                        }
                                      </strong>

                                      <span>
                                        {
                                          item.count
                                        }
                                      </span>

                                    </div>

                                  );
                                }
                              )
                          }

                        </div>


                        <div className="np-radar-stats">

                          {
                            radarStats.map(
                              item => (

                                <div
                                  className="np-radar-stat"
                                  key={item.name}
                                >

                                  <div className="np-radar-stat-top">

                                    <span>
                                      {
                                        item.name
                                      }
                                    </span>

                                    <strong>
                                      {
                                        item.count
                                      }
                                    </strong>

                                  </div>


                                  <div className="np-radar-bar">

                                    <span
                                      style={{
                                        width:
                                          `${(
                                            item.count /
                                            radarMaximum
                                          ) * 100}%`
                                      }}
                                    ></span>

                                  </div>

                                </div>

                              )
                            )
                          }

                        </div>


                        <div className="np-radar-summary">

                          <div>

                            <span>
                              BRIEFINGS
                            </span>

                            <strong>
                              {
                                history.length
                              }
                            </strong>

                          </div>


                          <div>

                            <span>
                              STORIES
                            </span>

                            <strong>
                              {
                                history.reduce(
                                  (
                                    total,
                                    entry
                                  ) =>
                                    total +
                                    entry
                                      .stories
                                      .length,
                                  0
                                )
                              }
                            </strong>

                          </div>


                          <div>

                            <span>
                              ACTIVE AREAS
                            </span>

                            <strong>
                              {
                                radarStats.length
                              }
                            </strong>

                          </div>

                        </div>

                      </>

                    )
                }

              </section>

            )
          }

        </div>

      </aside>

    </>

  );
}


export default NewsPulseExperienceHub;