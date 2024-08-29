<template>
  <div class="alert alert-danger mb-4" role="alert">
    <p>
      <i class="fas fa-exclamation-triangle"></i> Peer reviews must be requested on
      <strong>unpublished model releases</strong> so that you can continue to revise your submission
      based on reviewer guidance. If you have already published your model
      <strong>a new draft release will be created</strong> as an exact copy of your most recent
      published release.
    </p>
    <p class="mb-0">
      Once a model release passes peer review it will remain private until you choose to publish it,
      at which point you may set a version number. Please note that
      <strong>uploaded files cannot be modified after review</strong>
      regardless of published status, though metadata will remain editable.
    </p>
  </div>
  <p>
    Before submitting your peer review request, please ensure that your model conforms to the
    following <a href="/reviews/" target="_blank">review criteria</a>:
  </p>
  <div class="d-flex">
    <i class="fas fa-code pt-1" style="width: 1rem"></i>
    <div class="ps-3 flex-grow-1"><strong>Has "clean" source code</strong></div>
  </div>
  <small>
    <ul class="ps-5">
      <li>Uses meaningful variable, method, and/or class names</li>
      <li>Is well structured and consistently formatted for readability</li>
      <li>
        Has thorough comments that describe the semantics, intent, and assumptions of the code and
        its associated data structures, in every class | module | method | function
      </li>
      <li>
        Clearly documented inputs and outputs with properly described semantic types and adhering to
        community standard names (e.g.,
        <a href="https://csdms.colorado.edu/wiki/CSN_Searchable_List">CSDMS Standard Names</a>)
      </li>
      <li>
        <a href="https://en.wikiquote.org/wiki/Albert_Einstein"
          >"As simple as possible but no simpler"</a
        >
      </li>
    </ul>
  </small>
  <div class="d-flex">
    <i class="far fa-file-alt pt-1" style="width: 1rem"></i>
    <div class="ps-3 flex-grow-1"><strong>Has detailed narrative documentation</strong></div>
  </div>
  <small>
    <ul class="ps-5">
      <li>
        Contains equations, flowcharts, and other visual diagrams, and follows a structured
        documentation protocol like the
        <a href="https://doi.org/10.1016/j.ecolmodel.2010.08.019" target="_blank"
          >Overview, Design Concepts, and Details (ODD) protocol</a
        >
        or equivalent
      </li>
      <li>
        <strong>Do not submit a published journal article</strong> as narrative documentation
        <em>unless</em> it is 1. legally permissible to do so and 2. detailed enough to fully
        reproduce the model.
      </li>
    </ul>
  </small>
  <div class="d-flex">
    <i class="fas fa-terminal pt-1" style="width: 1rem"></i>
    <div class="ps-3 flex-grow-1"><strong>Is easily runnable</strong></div>
  </div>
  <small>
    <ul class="ps-5">
      <li>Has clear instructions for how to build, run, and parameterize the model</li>
      <li>
        Can be compiled (if needed) and run with minimal effort after downloading and extracting the
        published codebase
      </li>
      <li>
        Does not contain references to absolute paths that fail to resolve (e.g.
        <code>"/Users/turing/Desktop/ferns.nc"</code>)
      </li>
    </ul>
  </small>
  <div class="alert bg-gray" role="alert">
    <p><strong>Note on Uploaded Data</strong></p>
    <p class="mb-0">
      <small>
        The CoMSES Computational Model Library stores uploaded data files in
        <code>&lt;project-root&gt;/data/</code> and code in <code>&lt;project-root&gt;/code/</code>.
        Uploaded data files can be referenced by your model with a relative path like
        <code>"../data/my-input-data.csv"</code>. If you uploaded a zipfile with a nested directory
        structure you may need to go up several directories to get to the project root before
        descending back down into the data directory, depending on where your source code files
        exist within that nested directory structure. For example, a Python script in a
        <code>src/python/</code> directory would have to reference uploaded data files in
        <code>"../../../data/"</code>). This limitation can be circumvented by including your data
        in your source code zipfile, referencing relative paths to your input data directly in your
        code, and ignoring the CoMSES data upload slot.
      </small>
    </p>
  </div>
</template>

<script setup lang="ts"></script>
