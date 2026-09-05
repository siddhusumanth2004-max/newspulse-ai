import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import axios from "axios";

import "./App.css";


const BACKEND_PORT =
  process.env.REACT_APP_BACKEND_PORT ||
  "5000";


const BACKEND_URL =
  `${window.location.protocol}//${window.location.hostname}:${BACKEND_PORT}`;


const AUTO_REFRESH_SECONDS = 120;


// =====================================================
// APP
// =====================================================

function App() {

  const [activePage, setActivePage] =
    useState("dashboard");

  const [userRole, setUserRole] =
    useState("Student");

  const [limitPerSource, setLimitPerSource] =
    useState(2);

  const [maxStories, setMaxStories] =
    useState(3);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [result, setResult] =
    useState(null);


  // ===================================================
  // LIVE NEWS
  // ===================================================

  const [liveNews, setLiveNews] =
    useState([]);

  const [liveNewsLoading, setLiveNewsLoading] =
    useState(false);

  const [liveNewsError, setLiveNewsError] =
    useState("");

  const [lastUpdated, setLastUpdated] =
    useState(null);

  const [
    refreshCountdown,
    setRefreshCountdown
  ] = useState(
    AUTO_REFRESH_SECONDS
  );


  const refreshInFlight =
    useRef(false);


  // ===================================================
  // LIVING STORIES
  // ===================================================

  const [
    livingStories,
    setLivingStories
  ] = useState([]);

  const [
    storiesLoading,
    setStoriesLoading
  ] = useState(false);

  const [
    storiesError,
    setStoriesError
  ] = useState("");


  // ===================================================
  // SEARCH
  // ===================================================

  const [
    searchQuery,
    setSearchQuery
  ] = useState("");

  const [
    selectedStory,
    setSelectedStory
  ] = useState(null);


  // ===================================================
  // LOAD LIVE NEWS
  // ===================================================

  const loadLiveNews =
    useCallback(
      async ({
        silent = false
      } = {}) => {

        if (
          refreshInFlight.current
        ) {
          return;
        }


        refreshInFlight.current =
          true;


        try {

          if (!silent) {
            setLiveNewsLoading(true);
          }


          setLiveNewsError("");


          const response =
            await axios.get(
              `${BACKEND_URL}/api/news/latest`,
              {
                params: {
                  limit_per_source:
                    Number(
                      limitPerSource
                    ),

                  limit:
                    Number(
                      limitPerSource
                    )
                }
              }
            );


          const payload =
            response?.data?.data ??
            response?.data;


          const articles =
            Array.isArray(payload)
              ? payload
              : payload?.articles ||
                [];


          setLiveNews(
            Array.isArray(
              articles
            )
              ? articles
              : []
          );


          setLastUpdated(
            new Date()
          );


          setRefreshCountdown(
            AUTO_REFRESH_SECONDS
          );


        } catch (err) {

          console.error(
            "LIVE NEWS ERROR:",
            err
          );


          setLiveNewsError(
            err?.response
              ?.data?.message ||
            err?.message ||
            "Unable to load live news."
          );


        } finally {

          if (!silent) {
            setLiveNewsLoading(
              false
            );
          }


          refreshInFlight.current =
            false;

        }

      },
      [limitPerSource]
    );


  // ===================================================
  // LOAD LIVING STORIES
  // ===================================================

  const loadLivingStories =
    useCallback(
      async () => {

        try {

          setStoriesLoading(
            true
          );

          setStoriesError("");


          const response =
            await axios.get(
              `${BACKEND_URL}/api/stories`
            );


          const payload =
            response?.data?.data ??
            response?.data;


          setLivingStories(
            Array.isArray(payload)
              ? payload
              : []
          );


        } catch (err) {

          console.error(
            "STORY ERROR:",
            err
          );


          setStoriesError(
            err?.response
              ?.data?.message ||
            err?.message ||
            "Unable to load Living Stories."
          );


        } finally {

          setStoriesLoading(
            false
          );

        }

      },
      []
    );


  // ===================================================
  // INITIAL LOAD
  // ===================================================

  useEffect(() => {

    loadLivingStories();

  }, [
    loadLivingStories
  ]);


  useEffect(() => {

    loadLiveNews();

  }, [
    loadLiveNews
  ]);


  // ===================================================
  // LIVE COUNTDOWN
  // ===================================================

  useEffect(() => {

    const timer =
      setInterval(
        () => {

          setRefreshCountdown(
            (current) =>
              Math.max(
                current - 1,
                0
              )
          );

        },
        1000
      );


    return () =>
      clearInterval(timer);

  }, []);


  // ===================================================
  // AUTO REFRESH
  // ===================================================

  useEffect(() => {

    if (
      refreshCountdown === 0
    ) {

      loadLiveNews({
        silent: true
      });

    }

  }, [
    refreshCountdown,
    loadLiveNews
  ]);


  // ===================================================
  // GENERATE LANGCHAIN BRIEFING
  // ===================================================

  const generateBriefing =
    async () => {

      try {

        setLoading(true);

        setError("");


        const response =
          await axios.post(
            `${BACKEND_URL}/api/orchestrate`,
            {
              user_role:
                userRole,

              limit_per_source:
                Number(
                  limitPerSource
                ),

              similarity_threshold:
                0.50,

              max_stories:
                Number(
                  maxStories
                )
            }
          );


        const data =
          response?.data?.data ??
          response?.data;


        setResult(
          data
        );


        await loadLivingStories();


      } catch (err) {

        console.error(
          "ORCHESTRATOR ERROR:",
          err
        );


        const message =
          err?.response
            ?.data?.message ||
          err?.response
            ?.data?.detail ||
          err?.message ||
          "Unable to generate briefing.";


        setError(
          typeof message ===
            "string"
            ? message
            : JSON.stringify(
                message
              )
        );


      } finally {

        setLoading(false);

      }

    };


  // ===================================================
  // NAVIGATION
  // ===================================================

  const openPage =
    async (page) => {

      setActivePage(page);


      if (
        page === "living"
      ) {

        await loadLivingStories();

      }


      if (
        page === "briefing"
      ) {

        await loadLiveNews();

      }

    };


  // ===================================================
  // SEARCH
  // ===================================================

  const searchResults =
    useMemo(() => {

      const query =
        searchQuery
          .trim()
          .toLowerCase();


      if (!query) {
        return [];
      }


      const matches = [];


      // =================================================
      // LIVE NEWS
      // =================================================

      liveNews.forEach(
        (
          article,
          index
        ) => {

          const text = [

            article.title,

            article.summary,

            article.source

          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();


          if (
            text.includes(query)
          ) {

            matches.push({
              id:
                `live-${index}`,

              type:
                "live-news",

              title:
                article.title,

              summary:
                article.summary ||
                "",

              category:
                article.source ||
                "Live News",

              story:
                article
            });

          }

        }
      );


      // =================================================
      // CURRENT BRIEFING
      // =================================================

      result?.stories?.forEach(
        (
          story,
          index
        ) => {

          const briefing =
            story.briefing ||
            {};


          const sources =
            story.sources
              ?.map(
                (source) =>
                  `${source.source} ${source.title}`
              )
              .join(" ") ||
            "";


          const text = [

            briefing.headline,

            briefing.summary,

            briefing
              .what_happened,

            briefing
              .why_it_matters,

            briefing.category,

            sources

          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();


          if (
            text.includes(query)
          ) {

            matches.push({
              id:
                story
                  .living_story_id ||
                `brief-${index}`,

              type:
                "briefing",

              title:
                briefing.headline ||
                story
                  .representative_title,

              summary:
                briefing.summary ||
                "",

              category:
                briefing.category ||
                "General",

              story
            });

          }

        }
      );


      // =================================================
      // LIVING STORIES
      // =================================================

      livingStories.forEach(
        (story) => {

          const briefing =
            story
              .latest_briefing ||
            {};


          const text = [

            story.title,

            story.category,

            briefing.headline,

            briefing.summary,

            briefing
              .what_happened,

            briefing
              .why_it_matters

          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();


          if (
            text.includes(query)
          ) {

            const exists =
              matches.some(
                (item) =>
                  item.id ===
                  story.story_id
              );


            if (!exists) {

              matches.push({
                id:
                  story.story_id,

                type:
                  "living",

                title:
                  story.title ||
                  briefing.headline,

                summary:
                  briefing.summary ||
                  "",

                category:
                  story.category ||
                  briefing.category ||
                  "General",

                story
              });

            }

          }

        }
      );


      return matches;


    }, [
      searchQuery,
      liveNews,
      result,
      livingStories
    ]);


  const handleSearchChange =
    (event) => {

      const value =
        event.target.value;


      setSearchQuery(
        value
      );


      if (
        value.trim()
      ) {

        setActivePage(
          "search"
        );

      }

    };


  const openSearchResult =
    (item) => {

      setSelectedStory(
        item
      );

      setActivePage(
        "story-details"
      );

    };


  // ===================================================
  // PAGE TITLE
  // ===================================================

  const pageTitle = () => {

    switch (activePage) {

      case "dashboard":
        return "NewsPulse Dashboard";

      case "briefing":
        return "Live Briefing";

      case "living":
        return "Living Stories";

      case "evidence":
        return "Evidence Intelligence";

      case "impact":
        return "Impact Intelligence";

      case "search":
        return "Search Intelligence";

      case "story-details":
        return "Story Intelligence";

      default:
        return "NewsPulse";

    }

  };


  // ===================================================
  // RENDER
  // ===================================================

  return (

    <div className="app-shell">

      {/* ============================================== */}
      {/* SIDEBAR */}
      {/* ============================================== */}

      <aside className="sidebar">

        <div className="logo-area">

          <div className="logo-box">
            N
          </div>


          <div>

            <h1>
              NewsPulse
            </h1>

            <span>
              AI Intelligence
            </span>

          </div>

        </div>


        <nav className="nav-menu">

          <NavButton
            icon="⌂"
            text="Dashboard"
            page="dashboard"
            activePage={activePage}
            openPage={openPage}
          />


          <NavButton
            icon="◉"
            text="Live Briefing"
            page="briefing"
            activePage={activePage}
            openPage={openPage}
          />


          <NavButton
            icon="↻"
            text="Living Stories"
            page="living"
            activePage={activePage}
            openPage={openPage}
          />


          <NavButton
            icon="✓"
            text="Evidence"
            page="evidence"
            activePage={activePage}
            openPage={openPage}
          />


          <NavButton
            icon="◇"
            text="Impact"
            page="impact"
            activePage={activePage}
            openPage={openPage}
          />

        </nav>


        <div className="sidebar-bottom">

          <div className="system-status">

            <span className="online-dot" />

            <div>

              <strong>
                System Online
              </strong>

              <p>
                LangChain ready
              </p>

            </div>

          </div>

        </div>

      </aside>


      {/* ============================================== */}
      {/* MAIN */}
      {/* ============================================== */}

      <main className="main">

        <header className="header">

          <div className="header-title">

            <p className="header-small">
              NEWS INTELLIGENCE
            </p>

            <h2>
              {pageTitle()}
            </h2>

          </div>


          <div className="header-search">

            <span className="search-icon">
              ⌕
            </span>

            <input
              type="text"
              value={searchQuery}
              onChange={
                handleSearchChange
              }
              placeholder="Search news, topics, sources..."
            />


            {
              searchQuery && (

                <button
                  className="clear-search"
                  onClick={() => {

                    setSearchQuery("");

                    setActivePage(
                      "dashboard"
                    );

                  }}
                >
                  ×
                </button>

              )
            }

          </div>


          <div className="live-badge">

            <span className="live-dot" />

            LIVE

          </div>

        </header>


        <div className="content">

          {/* ========================================== */}
          {/* DASHBOARD */}
          {/* ========================================== */}

          {
            activePage ===
              "dashboard" && (

              <DashboardPage
                result={result}
                loading={loading}
                error={error}
                liveNews={liveNews}
                liveNewsLoading={
                  liveNewsLoading
                }
                liveNewsError={
                  liveNewsError
                }
                lastUpdated={
                  lastUpdated
                }
                refreshCountdown={
                  refreshCountdown
                }
                refreshLiveNews={() =>
                  loadLiveNews()
                }
                generateBriefing={
                  generateBriefing
                }
                openPage={
                  openPage
                }
              />

            )
          }


          {/* ========================================== */}
          {/* LIVE BRIEFING */}
          {/* ========================================== */}

          {
            activePage ===
              "briefing" && (

              <LiveBriefingPage
                result={result}
                loading={loading}
                error={error}
                liveNews={liveNews}
                liveNewsLoading={
                  liveNewsLoading
                }
                liveNewsError={
                  liveNewsError
                }
                lastUpdated={
                  lastUpdated
                }
                refreshCountdown={
                  refreshCountdown
                }
                refreshLiveNews={() =>
                  loadLiveNews()
                }
                generateBriefing={
                  generateBriefing
                }
              />

            )
          }


          {/* ========================================== */}
          {/* LIVING STORIES */}
          {/* ========================================== */}

          {
            activePage ===
              "living" && (

              <LivingStoriesPage
                stories={
                  livingStories
                }
                loading={
                  storiesLoading
                }
                error={
                  storiesError
                }
                refresh={
                  loadLivingStories
                }
                openStory={
                  (story) =>
                    openSearchResult({
                      id:
                        story.story_id,

                      type:
                        "living",

                      title:
                        story.title,

                      summary:
                        story
                          .latest_briefing
                          ?.summary ||
                        "",

                      category:
                        story.category,

                      story
                    })
                }
              />

            )
          }


          {/* ========================================== */}
          {/* EVIDENCE */}
          {/* ========================================== */}

          {
            activePage ===
              "evidence" && (

              <EvidencePage
                result={
                  result
                }
                openBriefing={() =>
                  openPage(
                    "briefing"
                  )
                }
              />

            )
          }


          {/* ========================================== */}
          {/* IMPACT */}
          {/* ========================================== */}

          {
            activePage ===
              "impact" && (

              <ImpactPage
                result={
                  result
                }
                openBriefing={() =>
                  openPage(
                    "briefing"
                  )
                }
              />

            )
          }


          {/* ========================================== */}
          {/* SEARCH */}
          {/* ========================================== */}

          {
            activePage ===
              "search" && (

              <SearchPage
                query={
                  searchQuery
                }
                results={
                  searchResults
                }
                openResult={
                  openSearchResult
                }
              />

            )
          }


          {/* ========================================== */}
          {/* STORY DETAIL */}
          {/* ========================================== */}

          {
            activePage ===
              "story-details" && (

              <StoryDetailsPage
                item={
                  selectedStory
                }
                goBack={() => {

                  if (
                    searchQuery.trim()
                  ) {

                    setActivePage(
                      "search"
                    );

                  } else {

                    setActivePage(
                      "dashboard"
                    );

                  }

                }}
              />

            )
          }

        </div>


        {/* ============================================== */}
        {/* STICKY CONTROL DOCK */}
        {/* ============================================== */}

        <StickyBriefingDock
          userRole={
            userRole
          }
          setUserRole={
            setUserRole
          }
          limitPerSource={
            limitPerSource
          }
          setLimitPerSource={
            setLimitPerSource
          }
          maxStories={
            maxStories
          }
          setMaxStories={
            setMaxStories
          }
          loading={
            loading
          }
          generateBriefing={
            generateBriefing
          }
        />

      </main>

    </div>

  );

}


// =====================================================
// NAV BUTTON
// =====================================================

function NavButton({
  icon,
  text,
  page,
  activePage,
  openPage
}) {

  return (

    <button
      className={
        activePage === page
          ? "nav-item active"
          : "nav-item"
      }
      onClick={() =>
        openPage(page)
      }
    >

      <span className="nav-icon">
        {icon}
      </span>

      {text}

    </button>

  );

}


// =====================================================
// STICKY DOCK
// =====================================================

function StickyBriefingDock({
  userRole,
  setUserRole,
  limitPerSource,
  setLimitPerSource,
  maxStories,
  setMaxStories,
  loading,
  generateBriefing
}) {

  return (

    <section className="sticky-control-dock">

      <DockControl
        icon="♙"
        label="Brief Me As"
        value={userRole}
        onChange={
          setUserRole
        }
        options={[
          "Student",
          "Developer",
          "Researcher",
          "Business Owner",
          "General Reader"
        ]}
      />


      <DockControl
        icon="▤"
        label="News / Source"
        value={
          limitPerSource
        }
        onChange={
          setLimitPerSource
        }
        options={[
          "1",
          "2",
          "3",
          "5"
        ]}
      />


      <DockControl
        icon="▦"
        label="Stories"
        value={
          maxStories
        }
        onChange={
          setMaxStories
        }
        options={[
          "1",
          "2",
          "3",
          "5"
        ]}
      />


      <button
        className="dock-generate-button"
        onClick={
          generateBriefing
        }
        disabled={
          loading
        }
      >

        <span>
          ✦
        </span>

        {
          loading
            ? "Analyzing..."
            : "Generate Briefing"
        }

      </button>

    </section>

  );

}


// =====================================================
// DOCK CONTROL
// =====================================================

function DockControl({
  icon,
  label,
  value,
  onChange,
  options
}) {

  return (

    <div className="dock-control">

      <div className="dock-label">

        <span className="dock-icon">
          {icon}
        </span>

        <span>
          {label}
        </span>

      </div>


      <select
        value={value}
        onChange={
          (event) =>
            onChange(
              event.target.value
            )
        }
      >

        {
          options.map(
            (option) => (

              <option
                key={option}
                value={option}
              >
                {option}
              </option>

            )
          )
        }

      </select>

    </div>

  );

}


// =====================================================
// DASHBOARD
// =====================================================

function DashboardPage({
  result,
  loading,
  error,
  liveNews,
  liveNewsLoading,
  liveNewsError,
  lastUpdated,
  refreshCountdown,
  refreshLiveNews,
  generateBriefing,
  openPage
}) {

  return (

    <>

      <section className="welcome-card">

        <div className="welcome-content">

          <span className="ai-label">
            LIVING NEWS AI
          </span>


          <h1 className="hero-title">

            Understand the news,

            <span>
              not just the headlines.
            </span>

          </h1>


          <p>

            NewsPulse tracks live stories,
            compares reports, remembers
            updates and explains what changed,
            why it matters and what to watch.

          </p>

        </div>


        <IntelligenceAnimation />

      </section>


      <LiveNewsSection
        articles={
          liveNews.slice(
            0,
            6
          )
        }
        loading={
          liveNewsLoading
        }
        error={
          liveNewsError
        }
        lastUpdated={
          lastUpdated
        }
        refreshCountdown={
          refreshCountdown
        }
        refresh={
          refreshLiveNews
        }
      />


      <StatusMessages
        loading={
          loading
        }
        error={
          error
        }
      />


      {
        result ? (

          <>

            <Stats
              result={
                result
              }
            />


            <section className="dashboard-actions">

              <button
                onClick={() =>
                  openPage(
                    "briefing"
                  )
                }
              >
                Full Briefing
              </button>

              <button
                onClick={() =>
                  openPage(
                    "living"
                  )
                }
              >
                Living Stories
              </button>

              <button
                onClick={() =>
                  openPage(
                    "evidence"
                  )
                }
              >
                Evidence
              </button>

              <button
                onClick={() =>
                  openPage(
                    "impact"
                  )
                }
              >
                Impact
              </button>

            </section>


            <div className="section-heading">

              <span>
                AI INTELLIGENCE
              </span>

              <h2>
                Latest Analyzed Stories
              </h2>

            </div>


            <div className="dashboard-story-grid">

              {
                result.stories?.map(
                  (
                    story,
                    index
                  ) => (

                    <StoryOverview
                      key={
                        story
                          .living_story_id ||
                        index
                      }
                      story={
                        story
                      }
                      number={
                        index + 1
                      }
                    />

                  )
                )
              }

            </div>

          </>

        ) : (

          !loading && (

            <div className="ai-ready-card">

              <div className="ai-ready-icon">
                ✦
              </div>


              <div>

                <span>
                  LANGCHAIN READY
                </span>

                <h3>
                  Turn live headlines into intelligence.
                </h3>

                <p>
                  Choose your options below and generate a briefing.
                </p>

              </div>


              <button
                onClick={
                  generateBriefing
                }
              >
                Analyze News
              </button>

            </div>

          )
        )
      }

    </>

  );

}


// =====================================================
// LIVE BRIEFING
// =====================================================

function LiveBriefingPage({
  result,
  loading,
  error,
  liveNews,
  liveNewsLoading,
  liveNewsError,
  lastUpdated,
  refreshCountdown,
  refreshLiveNews,
  generateBriefing
}) {

  return (

    <>

      <PageIntro
        label="LIVE INTELLIGENCE"
        title="Live News Briefing"
        text="Headlines automatically refresh every two minutes. Generate Briefing sends selected stories through LangChain and Claude."
      />


      <LiveNewsSection
        articles={
          liveNews
        }
        loading={
          liveNewsLoading
        }
        error={
          liveNewsError
        }
        lastUpdated={
          lastUpdated
        }
        refreshCountdown={
          refreshCountdown
        }
        refresh={
          refreshLiveNews
        }
      />


      <StatusMessages
        loading={
          loading
        }
        error={
          error
        }
      />


      {
        result &&
        !loading ? (

          <>

            <Stats
              result={
                result
              }
            />


            <div className="section-heading">

              <span>
                AI ANALYSIS
              </span>

              <h2>
                Intelligence Briefing
              </h2>

            </div>


            <div className="story-list">

              {
                result.stories?.map(
                  (
                    story,
                    index
                  ) => (

                    <FullStoryCard
                      key={
                        story
                          .living_story_id ||
                        index
                      }
                      story={
                        story
                      }
                      number={
                        index + 1
                      }
                    />

                  )
                )
              }

            </div>

          </>

        ) : (

          !loading && (

            <div className="briefing-placeholder">

              <span>
                LIVE NEWS READY
              </span>

              <h2>
                Headlines are updating automatically.
              </h2>

              <p>
                Run LangChain when you want the full AI intelligence briefing.
              </p>

              <button
                onClick={
                  generateBriefing
                }
              >
                Generate AI Briefing
              </button>

            </div>

          )
        )
      }

    </>

  );

}


// =====================================================
// LIVE NEWS SECTION
// =====================================================

function LiveNewsSection({
  articles,
  loading,
  error,
  lastUpdated,
  refreshCountdown,
  refresh
}) {

  return (

    <section className="live-news-section">

      <div className="live-news-header">

        <div>

          <div className="live-news-label">

            <span className="news-live-dot" />

            LIVE NEWS FEED

          </div>

          <h2>
            Latest Headlines
          </h2>

        </div>


        <button
          className="refresh-news-button"
          onClick={
            refresh
          }
          disabled={
            loading
          }
        >

          ↻

          {" "}

          {
            loading
              ? "Refreshing..."
              : "Refresh"
          }

        </button>

      </div>


      <div className="live-update-bar">

        <div>

          <span className="auto-live-dot" />

          <strong>
            AUTO LIVE
          </strong>

        </div>


        <span>

          Last updated:
          {" "}

          <b>
            {
              formatUpdateTime(
                lastUpdated
              )
            }
          </b>

        </span>


        <span>

          Next refresh:
          {" "}

          <b>
            {
              formatCountdown(
                refreshCountdown
              )
            }
          </b>

        </span>

      </div>


      {
        error && (

          <div className="live-news-error">
            {error}
          </div>

        )
      }


      {
        loading &&
        articles.length === 0 ? (

          <LoadingBox
            text="Collecting latest headlines..."
          />

        ) : articles.length > 0 ? (

          <div className="live-news-grid">

            {
              articles.map(
                (
                  article,
                  index
                ) => (

                  <LiveNewsCard
                    article={
                      article
                    }
                    number={
                      index + 1
                    }
                    key={
                      `${article.link || article.title}-${index}`
                    }
                  />

                )
              )
            }

          </div>

        ) : (

          !loading && (

            <div className="no-live-news">
              No headlines available right now.
            </div>

          )
        )
      }

    </section>

  );

}


// =====================================================
// LIVE NEWS CARD
// =====================================================

function LiveNewsCard({
  article,
  number
}) {

  return (

    <article className="live-news-card">

      <div className="live-card-top">

        <span className="live-card-number">

          {
            String(
              number
            ).padStart(
              2,
              "0"
            )
          }

        </span>


        <span className="publisher-chip">

          {
            article.source ||
            "News Source"
          }

        </span>

      </div>


      <h3>
        {article.title}
      </h3>


      {
        article.summary && (

          <p>
            {
              article.summary
            }
          </p>

        )
      }


      <div className="live-card-footer">

        <span>

          {
            article.published ||
            "Latest"
          }

        </span>


        {
          article.link && (

            <a
              href={
                article.link
              }
              target="_blank"
              rel="noreferrer"
            >
              Source →
            </a>

          )
        }

      </div>

    </article>

  );

}


// =====================================================
// INTELLIGENCE ANIMATION
// =====================================================

function IntelligenceAnimation() {

  return (

    <div className="intelligence-visual">

      <div className="pulse-ring ring-one" />
      <div className="pulse-ring ring-two" />
      <div className="pulse-ring ring-three" />


      <div className="orbit orbit-one">
        <span />
      </div>


      <div className="orbit orbit-two">
        <span />
      </div>


      <div className="intelligence-core">

        <strong>
          AI
        </strong>

        <div>

          <i />

          LIVE

        </div>

      </div>

    </div>

  );

}


// =====================================================
// LIVING STORIES
// =====================================================

function LivingStoriesPage({
  stories,
  loading,
  error,
  refresh,
  openStory
}) {

  return (

    <>

      <PageIntro
        label="STORY MEMORY"
        title="Living Stories"
        text="NewsPulse remembers stories and tracks how they change over time."
      />


      <div className="page-toolbar">

        <div>

          <strong>
            Saved Stories
          </strong>

          <span>
            {stories.length}
          </span>

        </div>


        <button
          onClick={
            refresh
          }
        >
          Refresh Stories
        </button>

      </div>


      {
        error && (

          <div className="error-box">
            {error}
          </div>

        )
      }


      {
        loading ? (

          <LoadingBox
            text="Loading story memory..."
          />

        ) : stories.length > 0 ? (

          <div className="living-grid">

            {
              stories.map(
                (story) => (

                  <LivingStoryCard
                    key={
                      story.story_id
                    }
                    story={
                      story
                    }
                    openStory={
                      openStory
                    }
                  />

                )
              )
            }

          </div>

        ) : (

          <EmptyState
            title="No Living Stories yet"
            text="Generate a briefing and NewsPulse will store the analyzed stories here."
            buttonText="Refresh"
            onClick={
              refresh
            }
          />

        )
      }

    </>

  );

}


// =====================================================
// EVIDENCE PAGE
// =====================================================

function EvidencePage({
  result,
  openBriefing
}) {

  return (

    <>

      <PageIntro
        label="TRUST LAYER"
        title="Evidence Intelligence"
        text="See how available sources support, contradict or remain neutral about important claims."
      />


      {
        result?.stories?.length > 0 ? (

          <div className="analysis-grid">

            {
              result.stories.map(
                (
                  story,
                  index
                ) => (

                  <article
                    className="analysis-card"
                    key={index}
                  >

                    <span className="analysis-index">

                      STORY
                      {" "}

                      {
                        String(
                          index + 1
                        ).padStart(
                          2,
                          "0"
                        )
                      }

                    </span>


                    <h2>
                      {
                        story.briefing
                          ?.headline
                      }
                    </h2>


                    {
                      story.evidence ? (

                        <>

                          <ConfidenceBadge
                            value={
                              story
                                .evidence
                                .confidence
                            }
                          />


                          <p className="analysis-summary">

                            {
                              story
                                .evidence
                                .evidence_summary
                            }

                          </p>


                          <EvidenceGroup
                            title="Supporting Sources"
                            items={
                              story
                                .evidence
                                .supporting_sources
                            }
                          />


                          <EvidenceGroup
                            title="Contradicting Sources"
                            items={
                              story
                                .evidence
                                .contradicting_sources
                            }
                          />


                          <EvidenceGroup
                            title="Neutral Sources"
                            items={
                              story
                                .evidence
                                .neutral_sources
                            }
                          />

                        </>

                      ) : (

                        <div className="notice-box">
                          {
                            story.evidence_note
                          }
                        </div>

                      )
                    }

                  </article>

                )
              )
            }

          </div>

        ) : (

          <EmptyState
            title="Generate a briefing first"
            text="Evidence appears after the LangChain intelligence agent analyzes stories."
            buttonText="Open Live Briefing"
            onClick={
              openBriefing
            }
          />

        )
      }

    </>

  );

}


// =====================================================
// IMPACT PAGE
// =====================================================

function ImpactPage({
  result,
  openBriefing
}) {

  return (

    <>

      <PageIntro
        label="IMPACT LAYER"
        title="Real-World Impact"
        text="Understand affected groups, risks, opportunities and what to watch next."
      />


      {
        result?.stories?.length > 0 ? (

          <div className="impact-page-grid">

            {
              result.stories.map(
                (
                  story,
                  index
                ) => {

                  const impact =
                    story.impact ||
                    {};


                  return (

                    <article
                      className="impact-page-card"
                      key={index}
                    >

                      <div className="impact-card-header">

                        <span>

                          STORY
                          {" "}

                          {
                            String(
                              index + 1
                            ).padStart(
                              2,
                              "0"
                            )
                          }

                        </span>


                        <ImpactBadge
                          level={
                            impact
                              .impact_level
                          }
                        />

                      </div>


                      <h2>

                        {
                          story.briefing
                            ?.headline
                        }

                      </h2>


                      <div className="personal-impact">

                        <span>
                          PERSONALIZED IMPACT
                        </span>

                        <p>

                          {
                            impact
                              .user_specific_impact
                          }

                        </p>

                      </div>


                      <ImpactGroups
                        groups={
                          impact
                            .impacted_groups
                        }
                      />


                      <div className="risk-grid">

                        <MiniList
                          title="Opportunities"
                          items={
                            impact
                              .opportunities
                          }
                        />

                        <MiniList
                          title="Risks"
                          items={
                            impact.risks
                          }
                        />

                      </div>


                      <div className="watch-box">

                        <span>
                          WHAT TO WATCH
                        </span>

                        <SimpleList
                          items={
                            impact
                              .what_to_watch
                          }
                        />

                      </div>

                    </article>

                  );

                }
              )
            }

          </div>

        ) : (

          <EmptyState
            title="Generate a briefing first"
            text="Impact appears after the AI intelligence agent analyzes the news."
            buttonText="Open Live Briefing"
            onClick={
              openBriefing
            }
          />

        )
      }

    </>

  );

}


// =====================================================
// SEARCH
// =====================================================

function SearchPage({
  query,
  results,
  openResult
}) {

  return (

    <>

      <PageIntro
        label="INTELLIGENCE SEARCH"
        title={`Search: "${query}"`}
        text="Search live headlines, AI briefings and Living Story memory."
      />


      <div className="search-summary">

        <strong>
          {results.length}
        </strong>

        <span>
          results found
        </span>

      </div>


      {
        results.length > 0 ? (

          <div className="search-results">

            {
              results.map(
                (item) => (

                  <button
                    className="search-result-card"
                    key={
                      `${item.type}-${item.id}`
                    }
                    onClick={() =>
                      openResult(
                        item
                      )
                    }
                  >

                    <div className="search-result-top">

                      <span className="search-type">

                        {
                          item.type ===
                          "living"
                            ? "LIVING STORY"
                            : item.type ===
                              "live-news"
                            ? "LIVE HEADLINE"
                            : "AI BRIEFING"
                        }

                      </span>


                      <span className="search-category">
                        {
                          item.category
                        }
                      </span>

                    </div>


                    <h2>
                      {item.title}
                    </h2>

                    <p>
                      {item.summary}
                    </p>


                    <div className="open-story">
                      Open →
                    </div>

                  </button>

                )
              )
            }

          </div>

        ) : (

          <EmptyState
            title="No matching stories"
            text="Try another keyword, company, category or source."
            buttonText="Clear Search"
            onClick={() =>
              window.location.reload()
            }
          />

        )
      }

    </>

  );

}


// =====================================================
// STORY DETAILS
// =====================================================

function StoryDetailsPage({
  item,
  goBack
}) {

  if (!item) {

    return (

      <EmptyState
        title="Story not selected"
        text="Choose a story first."
        buttonText="Back"
        onClick={
          goBack
        }
      />

    );

  }


  return (

    <>

      <button
        className="back-button"
        onClick={
          goBack
        }
      >
        ← Back
      </button>


      {
        item.type ===
        "briefing" ? (

          <FullStoryCard
            story={
              item.story
            }
            number={1}
          />

        ) : item.type ===
          "living" ? (

          <LivingStoryDetail
            story={
              item.story
            }
          />

        ) : (

          <LiveArticleDetail
            article={
              item.story
            }
          />

        )
      }

    </>

  );

}


// =====================================================
// LIVE ARTICLE DETAIL
// =====================================================

function LiveArticleDetail({
  article
}) {

  return (

    <article className="story-detail-card">

      <span className="story-detail-label">
        LIVE HEADLINE
      </span>

      <h1>
        {article.title}
      </h1>


      <div className="article-meta">

        <span>
          {article.source}
        </span>

        <span>
          {article.published}
        </span>

      </div>


      <p className="detail-summary">

        {
          article.summary ||
          "No feed summary available."
        }

      </p>


      {
        article.link && (

          <a
            href={
              article.link
            }
            target="_blank"
            rel="noreferrer"
            className="article-source-button"
          >
            Open Original Source →
          </a>

        )
      }

    </article>

  );

}


// =====================================================
// LIVING STORY DETAILS
// =====================================================

function LivingStoryDetail({
  story
}) {

  const briefing =
    story.latest_briefing ||
    {};


  return (

    <article className="story-detail-card">

      <span className="story-detail-label">
        LIVING STORY
      </span>

      <h1>

        {
          story.title ||
          briefing.headline
        }

      </h1>


      <p className="detail-summary">
        {briefing.summary}
      </p>


      <div className="story-detail-grid">

        <InformationBox
          title="What Happened"
        >
          <p>
            {
              briefing.what_happened
            }
          </p>
        </InformationBox>


        <InformationBox
          title="Why It Matters"
        >
          <p>
            {
              briefing.why_it_matters
            }
          </p>
        </InformationBox>

      </div>


      <section className="detail-section">

        <h3>
          Key Facts
        </h3>

        <SimpleList
          items={
            briefing.key_facts
          }
        />

      </section>


      <section className="timeline-section">

        <h2>
          Story Timeline
        </h2>


        {
          story.timeline
            ?.slice()
            .reverse()
            .map(
              (
                event,
                index
              ) => (

                <div
                  className="timeline-event"
                  key={index}
                >

                  <div className="timeline-dot" />


                  <div>

                    <span>
                      {
                        formatDate(
                          event.timestamp
                        )
                      }
                    </span>


                    <strong>

                      {
                        event.briefing
                          ?.headline
                      }

                    </strong>


                    {
                      event.delta && (

                        <div className="timeline-change">

                          <b>
                            What Changed
                          </b>

                          <p>

                            {
                              event.delta
                                .what_changed
                            }

                          </p>

                        </div>

                      )
                    }

                  </div>

                </div>

              )
            )
        }

      </section>

    </article>

  );

}


// =====================================================
// FULL AI STORY
// =====================================================

function FullStoryCard({
  story,
  number
}) {

  const briefing =
    story.briefing ||
    {};

  const evidence =
    story.evidence;

  const impact =
    story.impact ||
    {};

  const delta =
    story.delta;


  return (

    <article className="news-card">

      <div className="news-card-header">

        <div className="ranking">

          {
            String(
              number
            ).padStart(
              2,
              "0"
            )
          }

        </div>


        <div className="headline-area">

          <div className="story-tags">

            <span className="category-tag">

              {
                briefing.category ||
                "General"
              }

            </span>


            <span
              className={
                story.memory_action ===
                "UPDATED"
                  ? "memory-chip updated"
                  : "memory-chip created"
              }
            >

              {
                story.memory_action ===
                "UPDATED"
                  ? "Updated"
                  : "New Story"
              }

            </span>

          </div>


          <h2>
            {
              briefing.headline
            }
          </h2>

          <p className="summary">
            {
              briefing.summary
            }
          </p>

        </div>

      </div>


      <div className="story-information-grid">

        <InformationBox
          title="What Happened"
        >
          <p>
            {
              briefing.what_happened
            }
          </p>
        </InformationBox>


        <InformationBox
          title="Why It Matters"
        >
          <p>
            {
              briefing.why_it_matters
            }
          </p>
        </InformationBox>

      </div>


      {
        delta && (

          <section className="delta-card">

            <span className="delta-label">
              WHAT CHANGED
            </span>

            <h3>
              {
                delta.what_changed
              }
            </h3>


            <MiniList
              title="New Information"
              items={
                delta.new_information
              }
            />

          </section>

        )
      }


      <section className="detail-section">

        <h3>
          Key Facts
        </h3>

        <SimpleList
          items={
            briefing.key_facts
          }
        />

      </section>


      <section className="detail-section">

        <h3>
          Evidence
        </h3>


        {
          evidence ? (

            <div className="evidence-box">

              <ConfidenceBadge
                value={
                  evidence.confidence
                }
              />

              <p>
                {
                  evidence
                    .evidence_summary
                }
              </p>

              <small>
                {
                  evidence
                    .confidence_reason
                }
              </small>

            </div>

          ) : (

            <div className="notice-box">
              {
                story.evidence_note
              }
            </div>

          )
        }

      </section>


      <section className="detail-section">

        <h3>
          Real-World Impact
        </h3>

        <div className="impact-box">

          <ImpactBadge
            level={
              impact.impact_level
            }
          />

          <p>
            {
              impact
                .user_specific_impact
            }
          </p>

        </div>

      </section>


      <section className="sources-section">

        <h3>
          Sources
        </h3>


        {
          story.sources?.map(
            (
              source,
              index
            ) => (

              <a
                key={index}
                href={
                  source.link
                }
                target="_blank"
                rel="noreferrer"
                className="source-card"
              >

                <strong>
                  {
                    source.source
                  }
                </strong>

                <p>
                  {
                    source.title
                  }
                </p>

              </a>

            )
          )
        }

      </section>

    </article>

  );

}


// =====================================================
// STORY OVERVIEW
// =====================================================

function StoryOverview({
  story,
  number
}) {

  return (

    <article className="overview-card">

      <span className="overview-number">

        {
          String(
            number
          ).padStart(
            2,
            "0"
          )
        }

      </span>


      <h3>
        {
          story.briefing
            ?.headline
        }
      </h3>


      <p>
        {
          story.briefing
            ?.summary
        }
      </p>


      <div className="overview-footer">

        <span>
          {
            story.article_count
          }
          {" "}
          sources
        </span>

        <span>
          {
            story.briefing
              ?.category
          }
        </span>

      </div>

    </article>

  );

}


// =====================================================
// LIVING STORY CARD
// =====================================================

function LivingStoryCard({
  story,
  openStory
}) {

  return (

    <article className="living-card">

      <span className="living-label">
        LIVING STORY
      </span>


      <h2>

        {
          story.title ||
          story.latest_briefing
            ?.headline
        }

      </h2>


      <p>
        {
          story.latest_briefing
            ?.summary
        }
      </p>


      <div className="living-meta">

        <span>
          {story.category}
        </span>

        <span>

          {
            story.total_updates ||
            0
          }
          {" "}
          updates

        </span>

      </div>


      <button
        className="open-living-button"
        onClick={() =>
          openStory(
            story
          )
        }
      >
        Open Story →
      </button>

    </article>

  );

}


// =====================================================
// STATS
// =====================================================

function Stats({
  result
}) {

  const stats = [

    [
      "Articles",
      result
        .total_articles_collected
    ],

    [
      "Clusters",
      result
        .total_story_clusters
    ],

    [
      "Analyzed",
      result
        .analyzed_stories
    ],

    [
      "New",
      result
        .new_stories_created
    ],

    [
      "Updated",
      result
        .existing_stories_updated
    ]

  ];


  return (

    <section className="stats">

      {
        stats.map(
          (
            item,
            index
          ) => (

            <div
              className="metric-card"
              key={item[0]}
            >

              <div className="metric-icon">

                {
                  String(
                    index + 1
                  ).padStart(
                    2,
                    "0"
                  )
                }

              </div>


              <div>

                <strong>
                  {
                    item[1] ?? 0
                  }
                </strong>

                <span>
                  {item[0]}
                </span>

              </div>

            </div>

          )
        )
      }

    </section>

  );

}


// =====================================================
// HELPERS
// =====================================================

function PageIntro({
  label,
  title,
  text
}) {

  return (

    <section className="page-intro">

      <span>
        {label}
      </span>

      <h1>
        {title}
      </h1>

      <p>
        {text}
      </p>

    </section>

  );

}


function StatusMessages({
  loading,
  error
}) {

  return (

    <>

      {
        loading && (

          <LoadingBox
            text="Collect → Cluster → Memory → LangChain → Claude → Save"
          />

        )
      }


      {
        error && (

          <div className="error-box">

            <strong>
              Unable to generate briefing
            </strong>

            <span>
              {error}
            </span>

          </div>

        )
      }

    </>

  );

}


function LoadingBox({
  text
}) {

  return (

    <div className="loading-box">

      <div className="spinner" />

      <div>

        <h3>
          NewsPulse is working
        </h3>

        <p>
          {text}
        </p>

      </div>

    </div>

  );

}


function EmptyState({
  title,
  text,
  buttonText,
  onClick
}) {

  return (

    <section className="start-state">

      <div className="start-icon">
        N
      </div>

      <h3>
        {title}
      </h3>

      <p>
        {text}
      </p>

      <button
        onClick={
          onClick
        }
      >
        {buttonText}
      </button>

    </section>

  );

}


function InformationBox({
  title,
  children
}) {

  return (

    <div className="information-box">

      <h3>
        {title}
      </h3>

      {children}

    </div>

  );

}


function ConfidenceBadge({
  value
}) {

  const text =
    value ||
    "Unknown";


  const lower =
    text.toLowerCase();


  const className =
    lower.includes("high")
      ? "confidence high"
      : lower.includes(
          "medium"
        )
      ? "confidence medium"
      : "confidence low";


  return (

    <span
      className={
        className
      }
    >

      {text} Confidence

    </span>

  );

}


function ImpactBadge({
  level
}) {

  return (

    <span className="impact-badge">

      {
        level ||
        "Unknown"
      }
      {" "}
      Impact

    </span>

  );

}


function EvidenceGroup({
  title,
  items
}) {

  return (

    <div className="evidence-group">

      <strong>
        {title}
      </strong>

      <SimpleList
        items={
          items
        }
      />

    </div>

  );

}


function ImpactGroups({
  groups
}) {

  if (!groups?.length) {
    return null;
  }


  return (

    <div className="groups-grid">

      {
        groups.map(
          (
            group,
            index
          ) => (

            <div
              className="group-card"
              key={index}
            >

              <strong>
                {group.group}
              </strong>

              <p>
                {group.impact}
              </p>

              <span>
                {group.severity}
                {" · "}
                {group.timeframe}
              </span>

            </div>

          )
        )
      }

    </div>

  );

}


function MiniList({
  title,
  items
}) {

  return (

    <div className="mini-list">

      <strong>
        {title}
      </strong>

      <SimpleList
        items={
          items
        }
      />

    </div>

  );

}


function SimpleList({
  items
}) {

  if (!items?.length) {

    return (
      <p className="no-items">
        No major items identified.
      </p>
    );

  }


  return (

    <ul className="simple-list">

      {
        items.map(
          (
            item,
            index
          ) => (

            <li key={index}>
              {item}
            </li>

          )
        )
      }

    </ul>

  );

}


function formatDate(
  value
) {

  if (!value) {
    return "Unknown";
  }


  return new Date(
    value
  ).toLocaleString();

}


function formatUpdateTime(
  value
) {

  if (!value) {
    return "Loading...";
  }


  return value.toLocaleTimeString(
    [],
    {
      hour:
        "2-digit",

      minute:
        "2-digit"
    }
  );

}


function formatCountdown(
  seconds
) {

  const minutes =
    Math.floor(
      seconds / 60
    );


  const remaining =
    seconds % 60;


  return (
    `${String(minutes).padStart(2, "0")}:` +
    `${String(remaining).padStart(2, "0")}`
  );

}


export default App;