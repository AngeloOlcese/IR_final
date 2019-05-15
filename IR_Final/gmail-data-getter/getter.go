package main

import (
        "encoding/json"
        "fmt"
        "io/ioutil"
        "log"
        "net/http"
        "os"
        "encoding/base64"
        "strings"
        "strconv"


        "golang.org/x/net/context"
        "golang.org/x/oauth2"
        "golang.org/x/oauth2/google"
        "google.golang.org/api/gmail/v1"
)

type message struct {
	size     int64
	gmailID  string
	date     string // retrieved from message header
	snippet  string
  threadID string
  from     string
  subject  string
  to       string
  cc       string
  bcc      string
}

// Retrieve a token, saves the token, then returns the generated client.
func getClient(config *oauth2.Config) *http.Client {
        // The file token.json stores the user's access and refresh tokens, and is
        // created automatically when the authorization flow completes for the first
        // time.
        tokFile := "token.json"
        tok, err := tokenFromFile(tokFile)
        if err != nil {
                tok = getTokenFromWeb(config)
                saveToken(tokFile, tok)
        }
        return config.Client(context.Background(), tok)
}

// Request a token from the web, then returns the retrieved token.
func getTokenFromWeb(config *oauth2.Config) *oauth2.Token {
        authURL := config.AuthCodeURL("state-token", oauth2.AccessTypeOffline)
        fmt.Printf("Go to the following link in your browser then type the "+
                "authorization code: \n%v\n", authURL)

        var authCode string
        if _, err := fmt.Scan(&authCode); err != nil {
                log.Fatalf("Unable to read authorization code: %v", err)
        }

        tok, err := config.Exchange(context.TODO(), authCode)
        if err != nil {
                log.Fatalf("Unable to retrieve token from web: %v", err)
        }
        return tok
}

// Retrieves a token from a local file.
func tokenFromFile(file string) (*oauth2.Token, error) {
        f, err := os.Open(file)
        if err != nil {
                return nil, err
        }
        defer f.Close()
        tok := &oauth2.Token{}
        err = json.NewDecoder(f).Decode(tok)
        return tok, err
}

// Saves a token to a file path.
func saveToken(path string, token *oauth2.Token) {
        fmt.Printf("Saving credential file to: %s\n", path)
        f, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0600)
        if err != nil {
                log.Fatalf("Unable to cache oauth token: %v", err)
        }
        defer f.Close()
        json.NewEncoder(f).Encode(token)
}

func main() {
        b, err := ioutil.ReadFile("credentials.json")
        if err != nil {
                log.Fatalf("Unable to read client secret file: %v", err)
        }

        // If modifying these scopes, delete your previously saved token.json.
        config, err := google.ConfigFromJSON(b, gmail.GmailReadonlyScope)
        if err != nil {
                log.Fatalf("Unable to parse client secret file to config: %v", err)
        }
        client := getClient(config)

        svc, err := gmail.New(client)
        if err != nil {
                log.Fatalf("Unable to retrieve Gmail client: %v", err)
        }


      	var total int64
      	pageToken := ""
        count := 100
        limit := 125
      	for {
          req := svc.Users.Messages.List("me").Q("category:updates before:2017/12/01 after:2017/04/01")
          //req := svc.Users.Messages.List("me").Q("category:forums")
          //req := svc.Users.Messages.List("me").Q("category:personal")
          //req := svc.Users.Messages.List("me").Q("category:promotions")
          //req := svc.Users.Messages.List("me").Q("category:social")
          //req := svc.Users.Messages.List("me").Q("category:updates")

      		if pageToken != "" {
      			req.PageToken(pageToken)
      		}
      		r, err := req.Do()
      		if err != nil {
      			log.Fatalf("Unable to retrieve messages: %v", err)
      		}

      		log.Printf("Processing %v messages", len(r.Messages))
      		for _, m := range r.Messages {
      			msg, err := svc.Users.Messages.Get("me", m.Id).Format("full").Do()
      			if err != nil {
      				log.Fatalf("Unable to retrieve message %v: %v", m.Id, err)
      			}
      			total += msg.SizeEstimate

            for _, part := range msg.Payload.Parts {
              if count < limit {
                if part.PartId == "0" {
                  s, _ := base64.URLEncoding.DecodeString(part.Body.Data)
                  finalString := string(strings.TrimSpace(string(s)))
                  if finalString != "" {
                    fmt.Fprintln(os.Stdout, ".I " + strconv.FormatInt(int64(count), 10))
                    count++
                    hasLabel := false
                    //println("NewEmail labels: ")
                    for _, label := range msg.LabelIds {
                      if strings.Contains(label, "CATEGORY_FORUMS") {
                        fmt.Fprintln(os.Stdout, ".L 0")
                        hasLabel = true
                      } else if strings.Contains(label, "CATEGORY_PERSONAL") {
                        fmt.Fprintln(os.Stdout, ".L 1")
                        hasLabel = true
                      } else if strings.Contains(label, "CATEGORY_PROMOTIONS") {
                        fmt.Fprintln(os.Stdout, ".L 2")
                        hasLabel = true
                      } else if strings.Contains(label, "CATEGORY_SOCIAL") {
                        fmt.Fprintln(os.Stdout, ".L 3")
                        hasLabel = true
                      } else if strings.Contains(label, "CATEGORY_UPDATES") {
                        fmt.Fprintln(os.Stdout, ".L 4")
                        hasLabel = true
                      }
                      //println(label)
                    }
                    if !hasLabel {
                      println("No category label found")
                      continue
                    }

                    for _, h := range msg.Payload.Headers {
                      if h.Name == "Date" {
                        fmt.Fprintln(os.Stdout, ".D " + h.Value)
                      } else if h.Name == "From" {
                        fmt.Fprintln(os.Stdout, ".F " + h.Value)
                      } else if h.Name == "Subject" {
                        fmt.Fprintln(os.Stdout, ".S " + h.Value)
                      }
                    }
                    fmt.Fprintln(os.Stdout, ".M")
                    fmt.Fprintln(os.Stdout, finalString)
                  }
                }
                fmt.Fprintln(os.Stdout)
              }
            }
      		}
      		if r.NextPageToken == "" || count >= limit {
      			break
      		}
      		pageToken = r.NextPageToken
        }
}
