export default function SettingsPage() {
  return (
    <section>
      <h1 className="text-2xl font-semibold">Settings</h1>
      <p className="mt-3 max-w-2xl">
        Every agent uses Gemini through the model string google-gla:gemini-2.5-flash. Put GOOGLE_API_KEY or
        GEMINI_API_KEY in the repository .env file. The browser never receives that key. The web app sends only the
        application API_KEY from the server.
      </p>
    </section>
  );
}
