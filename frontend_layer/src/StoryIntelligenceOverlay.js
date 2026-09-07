import React, {
  useEffect,
  useMemo,
  useState
} from "react";

import axios from "axios";

import "./StoryIntelligenceOverlay.css";


// =====================================================
// NEWSPULSE
// STORY DNA + SOURCE DISAGREEMENT INTELLIGENCE
// =====================================================


const STORAGE_KEY =
  "newspulse_latest_story_intelligence";


// =====================================================
// SAFE ARRAY
// =====================================================

function safeArray(value) {

  return Array.isArray(value)
    ? value
    : [];

}


// =====================================================
// NORMALIZE CONFIDENCE
// =====================================================

function normalizeConfidence(value) {

  if (!value) {
    return "UNKNOWN";
  }


  const text =
    String(value)
      .trim()
      .toUpperCase();


  if (
    text.includes("HIGH")
  ) {
    return "HIGH";
  }


  if (
    text.includes("MEDIUM")
    ||
    text.includes("MODERATE")
  ) {
    return "MEDIUM";
  }


  if (
    text.includes("LOW")
  ) {
    return "LOW";
  }


  return text;

}


// =====================================================
// AGREEMENT CALCULATION
//
// Uses evidence that Claude already generated.
// No additional AI request.
// =====================================================

function calculateAgreement(story) {

  const evidence =
    story?.evidence ||
    {};


  const supporting =
    safeArray(
      evidence.supporting_sources
    ).length;


  const contradicting =
    safeArray(
      evidence.contradicting_sources
    ).length;


  const neutral =
    safeArray(
      evidence.neutral_sources
    ).length;


  if (
    supporting === 0
    &&
    contradicting === 0
    &&
    neutral === 0
  ) {

    return {
      label: "LIMITED",
      className: "limited"
    };

  }


  if (
    contradicting === 0
    &&
    supporting >= 2
  ) {

    return {
      label: "STRONG",
      className: "strong"
    };

  }


  if (
    contradicting === 0
    &&
    supporting >= 1
  ) {

    return {
      label: "ALIGNED",
      className: "aligned"
    };

  }


  if (
    supporting >
    contradicting
  ) {

    return {
      label: "MOSTLY ALIGNED",
      className: "mixed"
    };

  }


  if (
    contradicting >
    supporting
  ) {

    return {
      label: "DISPUTED",
      className: "disputed"
    };

  }


  return {
    label: "MIXED",
    className: "mixed"
  };

}


// =====================================================
// COUNT MEANINGFUL CHANGES
// =====================================================

function countChanges(story) {

  const delta =
    story?.delta;


  if (!delta) {
    return 0;
  }


  return (
    safeArray(
      delta.new_information
    ).length
    +
    safeArray(
      delta.changed_information
    ).length
    +
    safeArray(
      delta.corrected_information
    ).length
  );

}


// =====================================================
// DNA CREATOR
// =====================================================

function buildStoryDNA(story) {

  const evidence =
    story?.evidence ||
    {};


  const briefing =
    story?.briefing ||
    {};


  const impact =
    story?.impact ||
    {};


  const sourceCount =
    Number(
      story?.article_count
      ||
      story?.sources?.length
      ||
      0
    );


  const confidence =
    normalizeConfidence(
      evidence.confidence
      ||
      briefing.confidence
    );


  const agreement =
    calculateAgreement(
      story
    );


  const changes =
    countChanges(
      story
    );


  const impactLevel =
    impact.impact_level
      ? String(
          impact.impact_level
        ).toUpperCase()
      : "UNKNOWN";


  const memory =
    story?.memory_action
      ? String(
          story.memory_action
        ).toUpperCase()
      : "NEW";


  return {
    sourceCount,
    confidence,
    agreement,
    changes,
    impactLevel,
    memory
  };

}


// =====================================================
// EVIDENCE LIST
// =====================================================

function IntelligenceList({
  icon,
  title,
  items,
  type,
  emptyText
}) {

  const safeItems =
    safeArray(items);


  return (

    <section
      className={
        `np-intelligence-group ${type}`
      }
    >

      <div
        className="np-intelligence-group-title"
      >

        <span
          className="np-intelligence-group-icon"
        >
          {icon}
        </span>

        <span>
          {title}
        </span>

        <strong>
          {safeItems.length}
        </strong>

      </div>


      {
        safeItems.length > 0
          ? (

            <div
              className="np-intelligence-list"
            >

              {
                safeItems.map(
                  (
                    item,
                    index
                  ) => (

                    <div
                      className="np-intelligence-item"
                      key={
                        `${type}-${index}`
                      }
                    >

                      <span
                        className="np-intelligence-dot"
                      ></span>

                      <p>
                        {String(item)}
                      </p>

                    </div>

                  )
                )
              }

            </div>

          )
          : (

            <div
              className="np-intelligence-empty"
            >
              {emptyText}
            </div>

          )
      }

    </section>

  );

}


// =====================================================
// DNA METRIC
// =====================================================

function DNAMetric({
  label,
  value,
  type = ""
}) {

  return (

    <div
      className={
        `np-dna-metric ${type}`
      }
    >

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>

  );

}


// =====================================================
// MAIN COMPONENT
// =====================================================

function StoryIntelligenceOverlay() {

  const [
    latestResult,
    setLatestResult
  ] = useState(
    null
  );


  const [
    isOpen,
    setIsOpen
  ] = useState(
    false
  );


  const [
    selectedIndex,
    setSelectedIndex
  ] = useState(
    0
  );


  // ===================================================
  // RESTORE CURRENT SESSION INTELLIGENCE
  // ===================================================

  useEffect(
    () => {

      try {

        const stored =
          sessionStorage.getItem(
            STORAGE_KEY
          );


        if (stored) {

          const parsed =
            JSON.parse(
              stored
            );


          if (
            parsed
            &&
            Array.isArray(
              parsed.stories
            )
          ) {

            setLatestResult(
              parsed
            );

          }

        }

      }

      catch (error) {

        console.log(
          "NewsPulse DNA restore skipped.",
          error
        );

      }

    },
    []
  );


  // ===================================================
  // LISTEN TO ORCHESTRATOR RESPONSE
  //
  // App.js already uses the same axios instance.
  // We simply observe successful responses.
  // ===================================================

  useEffect(
    () => {

      const interceptor =
        axios
          .interceptors
          .response
          .use(

            (response) => {

              try {

                const url =
                  response
                    ?.config
                    ?.url
                  ||
                  "";


                if (
                  String(url)
                    .includes(
                      "/api/orchestrate"
                    )
                ) {

                  const payload =
                    response
                      ?.data
                      ?.data
                    ??
                    response
                      ?.data;


                  if (
                    payload
                    &&
                    Array.isArray(
                      payload.stories
                    )
                  ) {

                    setLatestResult(
                      payload
                    );


                    setSelectedIndex(
                      0
                    );


                    sessionStorage.setItem(
                      STORAGE_KEY,
                      JSON.stringify(
                        payload
                      )
                    );

                  }

                }

              }

              catch (error) {

                console.log(
                  "NewsPulse Story DNA capture skipped.",
                  error
                );

              }


              return response;

            },

            (error) => {

              return Promise.reject(
                error
              );

            }

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
  // STORIES
  // ===================================================

  const stories =
    useMemo(
      () => {

        return safeArray(
          latestResult?.stories
        );

      },
      [
        latestResult
      ]
    );


  // ===================================================
  // KEEP INDEX VALID
  // ===================================================

  useEffect(
    () => {

      if (
        selectedIndex
        >=
        stories.length
      ) {

        setSelectedIndex(
          0
        );

      }

    },
    [
      selectedIndex,
      stories.length
    ]
  );


  // ===================================================
  // CURRENT STORY
  // ===================================================

  const story =
    stories[
      selectedIndex
    ];


  const dna =
    useMemo(
      () => {

        if (!story) {
          return null;
        }


        return buildStoryDNA(
          story
        );

      },
      [
        story
      ]
    );


  // ===================================================
  // NOTHING GENERATED YET
  // ===================================================

  if (
    stories.length === 0
  ) {

    return null;

  }


  const evidence =
    story?.evidence ||
    {};


  const delta =
    story?.delta ||
    {};


  const headline =
    story?.briefing?.headline
    ||
    story?.representative_title
    ||
    "NewsPulse Story";


  // ===================================================
  // RENDER
  // ===================================================

  return (

    <>

      {/* ================================================
          FLOATING DNA BUTTON
          ================================================ */}

      <button
        type="button"
        className="np-dna-launcher"
        onClick={
          () => setIsOpen(
            true
          )
        }
        aria-label="Open Story DNA"
      >

        <span
          className="np-dna-launcher-core"
        >
          DNA
        </span>

        <span
          className="np-dna-launcher-text"
        >

          STORY
          <strong>
            INTELLIGENCE
          </strong>

        </span>

      </button>


      {/* ================================================
          BACKDROP
          ================================================ */}

      <div
        className={
          isOpen
            ? "np-dna-backdrop active"
            : "np-dna-backdrop"
        }
        onClick={
          () => setIsOpen(
            false
          )
        }
      ></div>


      {/* ================================================
          INTELLIGENCE DRAWER
          ================================================ */}

      <aside
        className={
          isOpen
            ? "np-dna-drawer active"
            : "np-dna-drawer"
        }
        aria-hidden={
          !isOpen
        }
      >

        {/* ==============================================
            TOP
            ============================================== */}

        <div
          className="np-dna-drawer-header"
        >

          <div>

            <span
              className="np-dna-eyebrow"
            >
              NEWSPULSE INTELLIGENCE
            </span>

            <h2>
              Story DNA
              <span>
                ✦
              </span>
            </h2>

          </div>


          <button
            type="button"
            className="np-dna-close"
            onClick={
              () => setIsOpen(
                false
              )
            }
            aria-label="Close Story DNA"
          >
            ×
          </button>

        </div>


        {/* ==============================================
            STORY SELECTOR
            ============================================== */}

        {
          stories.length > 1
          &&
          (

            <div
              className="np-dna-story-selector"
            >

              {
                stories.map(
                  (
                    item,
                    index
                  ) => (

                    <button
                      type="button"
                      key={
                        item?.living_story_id
                        ||
                        index
                      }
                      className={
                        selectedIndex ===
                        index
                          ? "active"
                          : ""
                      }
                      onClick={
                        () =>
                          setSelectedIndex(
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


        {/* ==============================================
            STORY
            ============================================== */}

        <div
          className="np-dna-scroll"
        >

          <section
            className="np-dna-story-heading"
          >

            <span>
              STORY
              {" "}
              {
                String(
                  selectedIndex + 1
                ).padStart(
                  2,
                  "0"
                )
              }
            </span>

            <h3>
              {headline}
            </h3>

            <p>
              {
                story?.briefing
                  ?.summary
                ||
                "NewsPulse intelligence analysis."
              }
            </p>

          </section>


          {/* ============================================
              STORY DNA
              ============================================ */}

          <section
            className="np-dna-panel"
          >

            <div
              className="np-dna-section-heading"
            >

              <div>

                <span>
                  INTELLIGENCE FINGERPRINT
                </span>

                <h3>
                  Story DNA
                </h3>

              </div>


              <div
                className="np-dna-pulse"
              >
                <span></span>
                <span></span>
                <span></span>
              </div>

            </div>


            <div
              className="np-dna-metrics"
            >

              <DNAMetric
                label="Sources"
                value={
                  dna.sourceCount
                }
              />


              <DNAMetric
                label="Confidence"
                value={
                  dna.confidence
                }
                type={
                  dna.confidence
                    .toLowerCase()
                }
              />


              <DNAMetric
                label="Agreement"
                value={
                  dna.agreement
                    .label
                }
                type={
                  dna.agreement
                    .className
                }
              />


              <DNAMetric
                label="Impact"
                value={
                  dna.impactLevel
                }
                type="impact"
              />


              <DNAMetric
                label="Changes"
                value={
                  dna.changes
                }
              />


              <DNAMetric
                label="Memory"
                value={
                  dna.memory
                }
                type="memory"
              />

            </div>

          </section>


          {/* ============================================
              SOURCE DISAGREEMENT
              ============================================ */}

          <section
            className="np-source-intelligence-panel"
          >

            <div
              className="np-dna-section-heading"
            >

              <div>

                <span>
                  MULTI-SOURCE ANALYSIS
                </span>

                <h3>
                  Source Intelligence
                </h3>

              </div>


              <div
                className={
                  `np-agreement-badge ${
                    dna.agreement
                      .className
                  }`
                }
              >

                {
                  dna.agreement
                    .label
                }

              </div>

            </div>


            {
              evidence
              &&
              (
                evidence.evidence_summary
                ||
                evidence.confidence_reason
              )
              &&
              (

                <div
                  className="np-evidence-summary"
                >

                  {
                    evidence.evidence_summary
                    &&
                    (
                      <p>
                        {
                          evidence
                            .evidence_summary
                        }
                      </p>
                    )
                  }


                  {
                    evidence.confidence_reason
                    &&
                    (
                      <small>
                        {
                          evidence
                            .confidence_reason
                        }
                      </small>
                    )
                  }

                </div>

              )
            }


            <IntelligenceList
              icon="✓"
              title="Supporting Sources"
              type="supporting"
              items={
                evidence
                  .supporting_sources
              }
              emptyText="No supporting-source list was returned."
            />


            <IntelligenceList
              icon="!"
              title="Contradicting Sources"
              type="contradicting"
              items={
                evidence
                  .contradicting_sources
              }
              emptyText="No direct source contradiction detected."
            />


            <IntelligenceList
              icon="○"
              title="Neutral Sources"
              type="neutral"
              items={
                evidence
                  .neutral_sources
              }
              emptyText="No neutral sources identified."
            />


            <IntelligenceList
              icon="?"
              title="Still Uncertain"
              type="uncertain"
              items={
                delta
                  .still_uncertain
              }
              emptyText="No unresolved items were identified."
            />

          </section>


          {/* ============================================
              FOOTER
              ============================================ */}

          <div
            className="np-dna-footer"
          >

            <span
              className="np-dna-live-dot"
            ></span>

            Generated from the current
            NewsPulse intelligence result.

          </div>

        </div>

      </aside>

    </>

  );

}


export default StoryIntelligenceOverlay;