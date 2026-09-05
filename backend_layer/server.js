const express =
  require("express");

const cors =
  require("cors");

const axios =
  require("axios");

const dotenv =
  require("dotenv");


dotenv.config();


const app =
  express();


const PORT =
  Number(
    process.env.PORT ||
    5000
  );


const HOST =
  process.env.HOST ||
  "0.0.0.0";


const AI_LAYER_URL =
  process.env.AI_LAYER_URL ||
  "http://127.0.0.1:8000";


const FRONTEND_URL =
  process.env.FRONTEND_URL ||
  "http://localhost:3000";


const REQUEST_TIMEOUT_MS =
  Number(
    process.env
      .REQUEST_TIMEOUT_MS ||
    180000
  );


// =====================================================
// PRIVATE NETWORK ORIGIN CHECK
// =====================================================

function isPrivateNetworkOrigin(
  origin
) {

  if (!origin) {
    return true;
  }


  // localhost
  if (
    /^http:\/\/localhost:\d+$/
      .test(origin)
  ) {
    return true;
  }


  // 127.0.0.1
  if (
    /^http:\/\/127\.0\.0\.1:\d+$/
      .test(origin)
  ) {
    return true;
  }


  // 192.168.x.x
  if (
    /^http:\/\/192\.168\.\d{1,3}\.\d{1,3}:\d+$/
      .test(origin)
  ) {
    return true;
  }


  // 10.x.x.x
  if (
    /^http:\/\/10\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$/
      .test(origin)
  ) {
    return true;
  }


  // 172.16.x.x - 172.31.x.x
  if (
    /^http:\/\/172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}:\d+$/
      .test(origin)
  ) {
    return true;
  }


  return false;

}


// =====================================================
// CORS
// =====================================================

app.use(
  cors({
    origin:
      function (
        origin,
        callback
      ) {

        if (
          origin ===
            FRONTEND_URL ||
          isPrivateNetworkOrigin(
            origin
          )
        ) {

          callback(
            null,
            true
          );

        } else {

          console.log(
            "Blocked CORS origin:",
            origin
          );


          callback(
            new Error(
              "Origin not allowed by CORS"
            )
          );

        }

      },

    methods: [
      "GET",
      "POST",
      "PUT",
      "PATCH",
      "DELETE",
      "OPTIONS"
    ],

    allowedHeaders: [
      "Content-Type",
      "Authorization",
      "x-internal-key"
    ]
  })
);


// =====================================================
// JSON
// =====================================================

app.use(
  express.json({
    limit: "10mb"
  })
);


// =====================================================
// AI CLIENT
// =====================================================

const aiClient =
  axios.create({
    baseURL:
      AI_LAYER_URL,

    timeout:
      REQUEST_TIMEOUT_MS,

    headers: {
      "Content-Type":
        "application/json"
    }
  });


// =====================================================
// ERROR HANDLER
// =====================================================

function handleAIError(
  error,
  res
) {

  console.error(
    "AI Layer Error:",
    error.message
  );


  if (
    error.response
  ) {

    return res
      .status(
        error.response.status ||
        500
      )
      .json({
        success: false,

        message:
          "AI Layer returned an error.",

        error:
          error.response.data
      });

  }


  if (
    error.request
  ) {

    return res
      .status(503)
      .json({
        success: false,

        message:
          "Unable to connect to AI Layer.",

        detail:
          `Make sure FastAPI is running at ${AI_LAYER_URL}`
      });

  }


  return res
    .status(500)
    .json({
      success: false,

      message:
        "Backend request failed.",

      detail:
        error.message
    });

}


// =====================================================
// ROOT
// =====================================================

app.get(
  "/",
  (
    req,
    res
  ) => {

    res.json({
      success: true,

      service:
        "NewsPulse Backend",

      status:
        "online",

      ai_layer:
        AI_LAYER_URL
    });

  }
);


// =====================================================
// HEALTH
// =====================================================

app.get(
  "/health",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.get(
          "/health"
        );


      res.json({
        success: true,

        backend:
          "healthy",

        ai_layer:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// ORCHESTRATE
// =====================================================

app.post(
  "/api/orchestrate",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.post(
          "/orchestrate",
          req.body
        );


      res.json({
        success: true,

        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// BRIEF
// =====================================================

app.post(
  "/api/brief",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.post(
          "/brief",
          req.body
        );


      res.json({
        success: true,
        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// DELTA
// =====================================================

app.post(
  "/api/delta",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.post(
          "/delta",
          req.body
        );


      res.json({
        success: true,
        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// EVIDENCE
// =====================================================

app.post(
  "/api/evidence",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.post(
          "/evidence",
          req.body
        );


      res.json({
        success: true,
        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// IMPACT
// =====================================================

app.post(
  "/api/impact",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.post(
          "/impact",
          req.body
        );


      res.json({
        success: true,
        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// LIVE NEWS
// =====================================================

app.get(
  "/api/news/latest",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.get(
          "/news/latest",
          {
            params: {
              ...req.query
            }
          }
        );


      res.json({
        success: true,

        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// NEWS CLUSTERS
// =====================================================

app.get(
  "/api/news/clusters",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.get(
          "/news/clusters",
          {
            params: {
              ...req.query
            }
          }
        );


      res.json({
        success: true,

        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// GET ALL STORIES
// =====================================================

app.get(
  "/api/stories",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.get(
          "/stories"
        );


      res.json({
        success: true,

        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// GET ONE STORY
// =====================================================

app.get(
  "/api/stories/:storyId",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.get(
          `/stories/${req.params.storyId}`
        );


      res.json({
        success: true,

        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// CREATE STORY
// =====================================================

app.post(
  "/api/stories",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.post(
          "/stories",
          req.body
        );


      res.json({
        success: true,

        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// UPDATE STORY
// =====================================================

app.post(
  "/api/stories/:storyId/update",
  async (
    req,
    res
  ) => {

    try {

      const response =
        await aiClient.post(
          `/stories/${req.params.storyId}/update`,
          req.body
        );


      res.json({
        success: true,

        data:
          response.data
      });


    } catch (error) {

      handleAIError(
        error,
        res
      );

    }

  }
);


// =====================================================
// 404
// =====================================================

app.use(
  (
    req,
    res
  ) => {

    res
      .status(404)
      .json({
        success: false,

        message:
          "NewsPulse route not found."
      });

  }
);


// =====================================================
// START SERVER
// =====================================================

app.listen(
  PORT,
  HOST,
  () => {

    console.log();
    console.log(
      "========================================"
    );

    console.log(
      "NEWSPULSE BACKEND STARTED"
    );

    console.log(
      "========================================"
    );

    console.log(
      `Host: ${HOST}`
    );

    console.log(
      `Backend Port: ${PORT}`
    );

    console.log(
      `AI Layer: ${AI_LAYER_URL}`
    );

    console.log(
      "Mobile LAN access enabled."
    );

    console.log(
      "========================================"
    );

  }
);